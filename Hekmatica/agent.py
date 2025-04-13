from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

import argparse

# Import BAML-generated client and types
from baml_client.sync_client import b  # BAML synchronous client
from baml_client.types import Clarification, Plan, Critique, ResultItem, RankedResultItem, Answer, ContextItem
from baml_client.tracing import trace, set_tags, flush, on_log_event

# Import tools
from tools import web_search, get_current_price

# Define the shared state for the agent's workflow
class AgentState(BaseModel):
    question: str
    clarification: Optional[Clarification] = None
    clarification_answer: Optional[str] = None
    subqueries: List[str] = []
    plan: Optional[Plan] = None
    raw_results: List[Dict[str, Optional[str]]] = []
    relevant_results: List[Dict[str, Optional[str]]] = []
    answer: Optional[Answer] = None
    critique: Optional[Critique] = None
    template_feedback: Optional[Dict[str, Any]] = None  # Store template-specific feedback
    attempt_count: int = 1  # number of answer attempts made (for loop control)

@trace
# Define node functions for each step in the workflow:
def clarify_node(state: AgentState):
    """Use LLM to determine if clarification is needed and generate a clarifying question."""
    state.clarification = b.ClarifyQuestion(question=state.question)
    return {"clarification": state.clarification}  # update state

@trace
def ask_user_node(state: AgentState):
    """Ask the user for clarification (if needed) and store the answer."""
    if state.clarification and state.clarification.needed:
        # Prompt the user and get input (in real usage, this would be interactive)
        user_input = input(f"Agent: {state.clarification.question} ")  # waiting for user
        state.clarification_answer = user_input.strip()
        # Optionally, update the question with clarification context (not strictly necessary)
    return {"clarification_answer": state.clarification_answer}

@trace
def generate_subqueries_node(state: AgentState):
    """Use LLM to generate multiple search subqueries for the question."""
    clarif_detail = state.clarification_answer or ""
    subqs = b.GenerateSubqueries(question=state.question, clarification_details=clarif_detail)
    # Ensure we have a list of strings (BAML returns a Python list for string[] output)
    state.subqueries = list(subqs) if isinstance(subqs, list) else subqs.queries  # .queries if wrapped in a model
    return {"subqueries": state.subqueries}

@trace
def plan_node(state: AgentState):
    """Use LLM to plan which tools to use for each aspect of the question."""
    state.plan = b.PlanSteps(question=state.question, subqueries=state.subqueries)
    return {"plan": state.plan}

@trace
def gather_info_node(state: AgentState):
    """Execute the plan: perform web searches and/or price lookups as specified, gather raw results."""
    results = []
    if state.plan:
        for step in state.plan.steps:
            tool = step.tool.value if hasattr(step.tool, "value") else str(step.tool)  # handle enum or string
            query = step.query
            if tool == "WebSearch":
                # Perform web search for this query - returns list of dicts
                search_res = web_search(query, max_results=5)
                results.extend(search_res) # Extend directly as it's already list of dicts
            elif tool == "PriceLookup":
                price_str = get_current_price(query)
                if price_str:
                    # Format price result as a dict for consistency
                    results.append({'content': f"Current {query} price: {price_str}", 'link': None})
                else:
                    results.append({'content': f"Current {query} price: (unavailable)", 'link': None})
    state.raw_results = results
    return {"raw_results": state.raw_results}

@trace
def filter_results_node(state: AgentState):
    """Use LLM via BAML to rank raw results and select the most relevant ones."""
    raw_results_dicts: List[Dict[str, Optional[str]]] = state.raw_results or []
    if not raw_results_dicts:
        state.relevant_results = []
        return {"relevant_results": state.relevant_results}

    # Convert Python dicts to BAML ResultItem instances
    raw_results_items = [ResultItem(content=d.get('content'), link=d.get('link')) for d in raw_results_dicts]

    # Define how many top results we want
    top_k_to_request = 5

    # Call the BAML function for ranking
    ranked_results_items: List[RankedResultItem] = b.RankResults(
        question=state.question,
        subqueries=state.subqueries,
        results=raw_results_items,
        top_k=top_k_to_request
    )

    # Convert the ranked BAML objects back to simple dictionaries for the state
    # We only keep content and link as defined in AgentState.relevant_results
    final_relevant_results = [
        {'content': item.content, 'link': item.link}
        for item in ranked_results_items
        # Optionally filter by score client-side too, though the LLM was asked to filter
        # if item.relevance_score >= 3
    ]

    state.relevant_results = final_relevant_results
    print(f"LLM Filtered Results (Top {len(state.relevant_results)}): {state.relevant_results}") # Add some logging

    return {"relevant_results": state.relevant_results}

@trace
def answer_node(state: AgentState):
    """Use LLM to generate a final answer from the question and relevant context."""
    relevant_context_dicts: List[Dict[str, Optional[str]]] = state.relevant_results or []
    
    # Create a list of ContextItem objects from the relevant results
    context_items: List[ContextItem] = []
    for res_dict in relevant_context_dicts:
        context_items.append(
            ContextItem(
                content=res_dict.get('content', ''), 
                source=res_dict.get('link') # Pass None if 'link' is missing
            )
        )
            
    # Call AnswerQuestion with the structured context list
    state.answer = b.AnswerQuestion(question=state.question, context=context_items)
    
    # Add some debug logging for the template structure
    if hasattr(state.answer, 'executive_summary'):
        print(f"Executive Summary: {state.answer.executive_summary[:100]}...")
    if hasattr(state.answer, 'key_points') and state.answer.key_points:
        print(f"Generated {len(state.answer.key_points)} key points")
    if hasattr(state.answer, 'confidence_score'):
        print(f"Answer confidence score: {state.answer.confidence_score:.2f}")
        
    return {"answer": state.answer}

@trace
def critique_node(state: AgentState):
    """Use LLM to critique the answer for completeness/correctness and template compliance."""
    # Format the answer to explicitly show template structure
    formatted_answer = ""
    if state.answer:
        # Create a clearly formatted version that shows section headings
        formatted_answer = (
            f"## Executive Summary\n{state.answer.executive_summary}\n\n"
            f"## Detailed Explanation\n{state.answer.detailed_explanation}\n\n"
            f"## Key Points\n"
        )
        # Add key points as bullet points
        if hasattr(state.answer, 'key_points') and state.answer.key_points:
            for point in state.answer.key_points:
                formatted_answer += f"- {point}\n"
        
        formatted_answer += f"\n## Complete Answer\n{state.answer.cited_answer}"
    else:
        # If no structured answer available, use just the cited_answer
        formatted_answer = state.answer.cited_answer if state.answer else ""
    
    # Send the formatted answer to the critique function
    state.critique = b.CritiqueAnswer(question=state.question, answer=formatted_answer)
    
    # Store template-specific feedback
    if state.critique:
        state.template_feedback = {
            "followed": state.critique.template_followed,
            "section_feedback": state.critique.section_feedback,
            "suggestions": state.critique.improvement_suggestions
        }
    
    return {
        "critique": state.critique,
        "template_feedback": state.template_feedback
    }

@trace
def additional_search_node(state: AgentState):
    """If the answer was insufficient, search for the missing information identified by critique."""
    missing = state.critique.missing_info if state.critique else ""
    missing = missing.strip()
    new_info_results: List[Dict[str, Optional[str]]] = [] # Expecting list of dicts
    
    # Check if we have template feedback
    template_issues = False
    if state.template_feedback:
        template_followed = state.template_feedback.get("followed", True)
        template_issues = not template_followed
        
        # If there are template issues but no specific missing info query,
        # we should still search to improve the answer content
        if template_issues and not missing:
            print("Template structure issues detected but no missing info specified.")
            # Use the original question as fallback if missing info isn't specific
            missing = state.question
            
        # Check for specific citation or source issues in the feedback
        elif "citation" in missing.lower() or "reference" in missing.lower():
            print(f"Citation issues detected: {missing}")
            # For citation issues, we might want to search for authoritative sources
            missing = f"authoritative sources {state.question}"
    
    if missing:
        print(f"Searching for additional information: {missing}")
        # Use the missing info string as a new search query
        new_info_results = web_search(missing, max_results=3) # Returns list of dicts
        
    # Append new search results (if any) to the relevant results for a second attempt
    if new_info_results:
        # Ensure we don't add duplicates (simple check based on link, if available)
        existing_links = {res.get('link') for res in state.relevant_results if res.get('link')}
        for new_res in new_info_results:
            if new_res.get('link') not in existing_links:
                 state.relevant_results.append(new_res)
            # Limit total relevant results if needed, e.g., state.relevant_results = state.relevant_results[-10:] 

    # Increment attempt count
    state.attempt_count += 1
    return {"relevant_results": state.relevant_results, "attempt_count": state.attempt_count}

class DeepResearchAgent:
    def __init__(self, graph: StateGraph, max_attempt_count: int = 2):
        self.graph = graph
        self.max_attempt_count = max_attempt_count

    def run(self, question: str, clarification_answer: str = None) -> str:
        # Initialize state with the question and optional pre-provided clarification answer
        state = AgentState(question=question, clarification_answer=clarification_answer)
        if clarification_answer:
            # If clarification answer is given, assume clarification was needed
            state.clarification = Clarification(needed=True, question="")  # dummy Clarification since user provided detail
        # Execute the graph
        final_state: AgentState = self.graph.invoke(state)  # Use invoke() instead of run()
        
        # Format the answer using template structure if available
        output = ""
        
        if final_state.get('answer'):
            answer = final_state['answer']
            
            # Check if we have the template fields
            has_template = (hasattr(answer, 'executive_summary') and 
                          hasattr(answer, 'detailed_explanation') and 
                          hasattr(answer, 'key_points'))
            
            if has_template:
                # Format with template structure
                output += f"## Executive Summary\n{answer.executive_summary}\n\n"
                output += f"## Detailed Explanation\n{answer.detailed_explanation}\n\n"
                
                # Format key points as bullet list
                output += "## Key Points\n"
                for point in answer.key_points:
                    output += f"- {point}\n"
                output += "\n"
                
                # Add confidence if available
                if hasattr(answer, 'confidence_score'):
                    output += f"_Answer confidence: {answer.confidence_score:.2f}/1.0_\n\n"
            else:
                # Fall back to cited_answer if template isn't available
                output = answer.cited_answer
            
            # Add template feedback note if there are template issues
            template_note = ""
            if final_state.get('template_feedback') and not final_state['template_feedback'].get('followed', True):
                template_note = "\n\n**Note:** This answer could be improved by following the recommended template structure."
                
                # If there are specific improvement suggestions, include the first 2
                if 'suggestions' in final_state['template_feedback'] and final_state['template_feedback']['suggestions']:
                    template_note += "\nSuggested improvements:"
                    for i, suggestion in enumerate(final_state['template_feedback']['suggestions'][:2]):
                        template_note += f"\n- {suggestion}"
            
            output += template_note
            
            # Process and add references if available
            if hasattr(answer, 'references') and answer.references:
                 # Create a list of tuples (index, formatted_string) for sorting
                 raw_references = []
                 for ref in answer.references:
                     if ref.source:
                         # Store index as integer for proper sorting
                         raw_references.append((ref.index, f"[{ref.index}] {ref.source}"))

                 # Sort based on the index
                 raw_references.sort(key=lambda item: item[0])

                 # Extract the sorted formatted strings
                 references_list = [item[1] for item in raw_references]
                 
                 # Add references section
                 if references_list:
                     output += "\n\n## References\n" + "\n".join(f"- {ref_source}" for ref_source in references_list)
            
        # If no answer was generated, provide a helpful message
        return output or "No answer could be generated. Please try rephrasing your question."

def build_agent_graph():
    # Build the LangGraph state graph
    graph_builder = StateGraph(AgentState)

    # Add nodes to the graph
    graph_builder.add_node("clarify", clarify_node)
    graph_builder.add_node("ask_user", ask_user_node)
    graph_builder.add_node("generate_subqueries", generate_subqueries_node)
    graph_builder.add_node("generate_plan", plan_node)
    graph_builder.add_node("gather_info", gather_info_node)
    graph_builder.add_node("filter_results", filter_results_node)
    graph_builder.add_node("generate_answer", answer_node)
    graph_builder.add_node("generate_critique", critique_node)
    graph_builder.add_node("additional_search", additional_search_node)

    # Define edges and conditional edges
    graph_builder.set_entry_point("clarify") # Use set_entry_point instead of add_edge from START

    # Conditional edge after clarify: Decide whether to ask user or generate subqueries
    def decide_clarification_path(state: AgentState):
        if state.clarification and state.clarification.needed and not state.clarification_answer:
            return "ask_user"
        else:
            return "generate_subqueries"

    graph_builder.add_conditional_edges(
        "clarify",
        decide_clarification_path,
        {
            "ask_user": "ask_user",
            "generate_subqueries": "generate_subqueries",
        }
    )

    # After asking user, always proceed to subqueries generation
    graph_builder.add_edge("ask_user", "generate_subqueries")

    graph_builder.add_edge("generate_subqueries", "generate_plan")
    graph_builder.add_edge("generate_plan", "gather_info")
    graph_builder.add_edge("gather_info", "filter_results")
    graph_builder.add_edge("filter_results", "generate_answer")
    graph_builder.add_edge("generate_answer", "generate_critique")

    # Conditional edge after critique: Decide whether to end or do additional search
    def decide_critique_path(state: AgentState):
        if state.critique and (state.critique.is_good or state.attempt_count >= 2):
            return END
        elif state.critique and not state.critique.is_good and state.attempt_count < 2:
            return "additional_search"
        else:
            # Fallback case, should ideally not be reached if critique is always present
            # but good practice to handle it. Defaulting to END.
            print("Warning: Unexpected state in critique branching, ending.")
            return END

    graph_builder.add_conditional_edges(
        "generate_critique",
        decide_critique_path,
        {
            END: END, # Map the special END value
            "additional_search": "additional_search",
        }
    )

    # After gathering additional info, go back to generate a new answer and critique again
    graph_builder.add_edge("additional_search", "generate_answer")

    # Build the graph
    agent_graph = graph_builder.compile()
    return agent_graph

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Deep Research Agent")
    parser.add_argument("--question", type=str, help="The question to research")
    args = parser.parse_args()

    agent_graph = build_agent_graph()
    agent = DeepResearchAgent(agent_graph)
    user_question = (
        args.question
        or "What were the key factors leading to the fall of the Roman Empire?"
    )
    print(f"User: {user_question}")
    # Run the agent (this will ask for clarification interactively if needed)
    final_output_string = agent.run(user_question) # Returns a string with answer + references
    # Print the final output string
    print(f"Agent Output:\n{final_output_string}")
