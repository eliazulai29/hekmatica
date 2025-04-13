// Define a class to represent a structured context item
class ContextItem {
  content string
  source string? // Source/link is optional
}

class Source {
  index int
  source string
  source_type string
}
// AnswerQuestion: Compose a final answer using the question and structured context info
class Answer {
  executive_summary string @description("Brief 1-2 sentence answer to the question")
  detailed_explanation string @description("Comprehensive answer with all relevant details")
  key_points string[] @description("List of important takeaways in bullet-point format")
  cited_answer string @description("The final answer with inline citations like [0], [1] referring to the context items.")
  references Source[] @description("A numerical list of source URLs/identifiers corresponding to the citations used in the answer.")
  confidence_score float @description("A score from 0-1 indicating confidence in the answer")
}

// Updated function signature to accept a list of ContextItem objects
function AnswerQuestion(question: string, context: ContextItem[]) -> Answer {
  client CustomGPT4oMini

  prompt #"""
    You are an expert writing a detailed answer to the user's question using the provided structured context information.
    
    Your answer MUST follow this template structure:
    1. Executive Summary: A concise 1-2 sentence overview that directly answers the question
    2. Detailed Explanation: A comprehensive, well-organized explanation with all relevant information
    3. Key Points: 3-5 bullet points highlighting the most important takeaways
    4. Full Answer with Citations: Integrate information naturally with bracketed citations [0], [1], etc.
    
    After generating your answer, rate your confidence from 0-1 based on the completeness of context.
    
    Use the context items to ensure accuracy and completeness.
    **Cite the context items used for each part of your answer using bracketed numbers corresponding to the list below (e.g., [0], [1]).**
    Integrate the information naturally. Do not just list the context content verbatim.
    If the context contains a current price or specific data, include it in the answer with its citation.
    After generating the full answer with citations, list all the `source` fields from the context items you actually cited in the `references` field. Only include sources that were cited. If a cited item has no source, omit it from the references list.
    The answer should fully address the question.

    Question: {{ question }}

    Context Items:
    // Updated context loop to iterate over ContextItem objects and access their fields
    {% for item in context %}
    [{{ loop.index0 }}] Content: {{ item.content }}
       Source: {{ item.source or "N/A" }}
    {% endfor %}

    ----
    {{ ctx.output_format }}
  """#
}

// Tests for AnswerQuestion
test answer_with_general_context {
  functions [AnswerQuestion]
  args {
    question "How does photosynthesis work in plants?"
    context [
      { 
        content "Photosynthesis uses sunlight, water, and carbon dioxide to create glucose (sugar) and oxygen.", 
        source "http://example.com/photosynthesis-basics" 
      },
      { 
        content "Chlorophyll, the green pigment in leaves, absorbs sunlight.", 
        source "http://example.com/chlorophyll-role"
      },
      { 
        content "The process primarily occurs in chloroplasts within plant cells.", 
        source "http://example.com/chloroplasts" 
      },
      { 
        content "Oxygen is released as a byproduct.", 
        source null // Example with no source
      }
    ]
  }
  @@assert({{ this.cited_answer != ""}})
  @@assert({{ "glucose" in this.cited_answer or "oxygen" in this.cited_answer or "chlorophyll" in this.cited_answer }})
  @@assert({{ "[0]" in this.cited_answer or "[1]" in this.cited_answer or "[2]" in this.cited_answer or "[3]" in this.cited_answer }})
  // Check if references are generated correctly (at least the ones with sources)
  @@assert({{ this.references | length >= 2 }})
  @@assert({{ "http://example.com/photosynthesis-basics" in (this.references | map(attribute='source') | list) }})
  // Check if the template fields are populated
  @@assert({{ this.executive_summary != "" }})
  @@assert({{ this.detailed_explanation != "" }})
  @@assert({{ this.key_points | length >= 3 }})
  @@assert({{ this.confidence_score >= 0.0 and this.confidence_score <= 1.0 }})
}

// New test for templated output
test answer_with_template_structure {
  functions [AnswerQuestion]
  args {
    question "What are the effects of climate change on ocean ecosystems?"
    context [
      { 
        content "Rising ocean temperatures are causing coral bleaching events worldwide.", 
        source "http://example.com/coral-bleaching" 
      },
      { 
        content "Ocean acidification reduces the ability of marine organisms to build calcium carbonate shells and skeletons.", 
        source "http://example.com/ocean-acidification"
      },
      { 
        content "Sea level rise threatens coastal habitats like mangroves and salt marshes.", 
        source "http://example.com/sea-level-impacts" 
      },
      { 
        content "Changing ocean currents affect nutrient distribution and marine food webs.", 
        source "http://example.com/ocean-currents" 
      }
    ]
  }
  // Check if the template sections are populated correctly
  @@assert({{ this.executive_summary != "" and this.executive_summary | length < 200 }})
  @@assert({{ this.detailed_explanation != "" and this.detailed_explanation | length > 200 }})
  @@assert({{ this.key_points | length >= 3 and this.key_points | length <= 5 }})
  @@assert({{ this.cited_answer != "" }})
  @@assert({{ "[0]" in this.cited_answer and "[1]" in this.cited_answer }})
  @@assert({{ this.references | length >= 3 }})
  @@assert({{ this.confidence_score >= 0.0 and this.confidence_score <= 1.0 }})
}
