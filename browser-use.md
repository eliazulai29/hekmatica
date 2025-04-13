# Browser-use: Enable AI to Control Your Browser

## Overview

Browser-use is a powerful Python library that enables AI agents to control web browsers programmatically. It provides a seamless interface between AI models and web browsers, allowing agents to perform complex web tasks such as form filling, data extraction, navigation, and interaction with web elements. The library is designed to be model-agnostic, supporting various LLM providers including OpenAI, Anthropic, Google, and others.

## Architecture

The browser-use library is organized into several core modules:

### Core Components

1. **Agent**: The central component that handles the interaction between the AI model and the browser. It manages the task execution flow, maintains conversation history, and coordinates actions.

2. **Browser**: Manages the browser instance using Playwright under the hood. It provides methods to create browser contexts and control browser behavior.

3. **Controller**: Registers and manages available actions that an agent can perform, such as clicking buttons, navigating to URLs, typing text, etc.

4. **DOM Service**: Handles DOM parsing and extraction, providing a structured representation of web pages for the AI to understand.

5. **Telemetry**: Collects usage metrics and performance data to help improve the library.

## Key Modules

### agent/ 

The agent module is responsible for coordinating the interaction between LLMs and the browser:

- **service.py**: Contains the main `Agent` class which orchestrates the entire process
- **memory/**: Manages the agent's memory for long-term contextual understanding
- **message_manager/**: Handles prompt formatting and message history
- **prompts.py**: Defines system prompts and prompt templates
- **views.py**: Contains data models for agent state and actions

The agent follows a loop pattern:
1. Get the current browser state
2. Format the state into a prompt for the LLM
3. Get the next action from the LLM
4. Execute the action on the browser
5. Repeat

### browser/

The browser module is responsible for browser management and control:

- **browser.py**: Contains the `Browser` class that initializes and manages browser instances
- **context.py**: Manages browser contexts (similar to profiles)
- **chrome.py**: Defines Chrome-specific configurations and arguments
- **utils/**: Helper functions for browser operations

The browser component supports multiple connection methods:
- Built-in browsers (using Playwright)
- User's installed browsers
- Remote browsers via WebSocket or CDP

### controller/

The controller module manages available actions and their execution:

- **service.py**: Contains the `Controller` class that manages actions
- **registry/**: Handles registration and filtering of available actions
- **views.py**: Data models for actions and their parameters

### dom/

The DOM module handles web page parsing and element extraction:

- **service.py**: Contains the `DomService` class for parsing HTML
- **buildDomTree.js**: JavaScript code for extracting structured DOM information
- **history_tree_processor/**: Processes DOM history for better context understanding

## Key Features

1. **Vision-enabled AI**: Can use vision capabilities of models like GPT-4V to interpret screenshots

2. **Memory Management**: Long-term memory for complex multi-step tasks

3. **Multi-browser Support**: Works with Chromium, Firefox, and WebKit browsers

4. **LLM Provider Agnostic**: Compatible with OpenAI, Anthropic, Google, and other providers

5. **Customizable Actions**: Extendable with custom actions and functions

6. **Security Features**: Configurable security settings to prevent malicious activity

7. **Telemetry**: Optional usage tracking for improving the library

8. **Error Handling**: Robust error handling and recovery mechanisms

## Usage Patterns

### Basic Usage

```python
from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio

async def main():
    agent = Agent(
        task="Compare the price of GPT-4o and Claude 3 Opus",
        llm=ChatOpenAI(model="gpt-4o"),
    )
    await agent.run()

asyncio.run(main())
```

### Custom Browser Configuration

```python
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
import asyncio

async def main():
    browser_config = BrowserConfig(
        headless=False,
        disable_security=False,
        browser_class="chromium"
    )
    
    browser = Browser(config=browser_config)
    
    agent = Agent(
        task="Find the cheapest flight from New York to San Francisco",
        llm=ChatOpenAI(model="gpt-4o"),
        browser=browser
    )
    
    await agent.run()

asyncio.run(main())
```

### With Sensitive Data Handling

```python
from browser_use import Agent
from langchain_openai import ChatOpenAI
import asyncio
import os

async def main():
    sensitive_data = {
        "email": os.environ.get("USER_EMAIL"),
        "password": os.environ.get("USER_PASSWORD")
    }
    
    agent = Agent(
        task="Log into my email and summarize unread messages",
        llm=ChatOpenAI(model="gpt-4o"),
        sensitive_data=sensitive_data
    )
    
    await agent.run()

asyncio.run(main())
```

## Real-World Examples

The browser-use library includes several real-world examples that demonstrate its capabilities in practical scenarios.

### Online Grocery Shopping

One impressive example is the online grocery shopping agent found in `examples/use-cases/shopping.py`. This agent:

1. Navigates to an online grocery store (Migros Online)
2. Logs into an existing account
3. Searches for and adds items from a shopping list to the cart
4. Handles product substitutions for unavailable items
5. Ensures the order meets minimum requirements
6. Selects a delivery window
7. Completes the checkout process using a specific payment method
8. Summarizes the order details

Here's how it's implemented:

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser
import asyncio

load_dotenv()

task = """
   ### Prompt for Shopping Agent – Migros Online Grocery Order

**Objective:**
Visit [Migros Online](https://www.migros.ch/en), search for the required grocery items, 
add them to the cart, select an appropriate delivery window, and complete the checkout 
process using TWINT.

**Important:**
- Make sure that you don't buy more than it's needed for each article.
- After your search, if you click the "+" button, it adds the item to the basket.
- if you open the basket sidewindow menu, you can close it by clicking the X button 
  on the top right. This will help you navigate easier.

### Step 1: Navigate to the Website
- Open [Migros Online](https://www.migros.ch/en).
- You should be logged in as Nikolaos Kaliorakis

### Step 2: Add Items to the Basket

#### Shopping List:
**Meat & Dairy:**
- Beef Minced meat (1 kg)
- Gruyère cheese (grated preferably)
- 2 liters full-fat milk
- Butter (cheapest available)

**Vegetables:**
- Carrots (1kg pack)
- Celery
- Leeks (1 piece)
- 1 kg potatoes

[...additional shopping instructions...]

### Step 7: Confirm Order & Output Summary
- Once the order is placed, output a summary including:
  - **Final list of items purchased** (including any substitutions).
  - **Total cost**.
  - **Chosen delivery time**.
"""

browser = Browser()

agent = Agent(
    task=task,
    llm=ChatOpenAI(model='gpt-4o'),
    browser=browser,
)

async def main():
    await agent.run()
    input('Press Enter to close the browser...')
    await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
```

This example demonstrates how browser-use can automate complex multi-step processes that previously required human intervention. The agent is capable of:

- **Contextual understanding**: It knows which products to substitute based on recipe requirements
- **Decision making**: It can adjust the cart to meet minimum order requirements
- **Form navigation**: It can complete the entire checkout process
- **Error handling**: It can handle out-of-stock items and age verification prompts

Other real-world examples included in the library demonstrate tasks like:
- Job application automation
- Social media posting
- Appointment scheduling
- Web research with data extraction

These examples show the flexibility of browser-use for automating a wide range of web-based workflows.

## Integration with AI Frameworks

Browser-use is designed to work seamlessly with various AI frameworks and agent systems. One powerful integration possibility is with research and knowledge-work frameworks like Hekmatica.

### Integration with Hekmatica

[Hekmatica](https://github.com/eliazulai29/hekmatica) is an AI research agent framework that excels at deep research, document analysis, and generating comprehensive answers with proper citations. Combining browser-use with Hekmatica creates a powerful system that can:

1. **Conduct web-based research** using browser-use to navigate to relevant sources
2. **Extract and analyze information** from web pages
3. **Process the information** through Hekmatica's research and citation pipeline
4. **Generate comprehensive, cited reports** based on web findings

Here's an example integration approach:

```python
import asyncio
from browser_use import Agent as BrowserAgent, Browser
from langchain_openai import ChatOpenAI
from hekmatica import DeepResearchAgent

async def web_research_task(query, sensitive_data=None):
    # Initialize browser and agent
    browser = Browser()
    browser_agent = BrowserAgent(
        task=f"Research information about: {query}. Extract key facts and save them to a file.",
        llm=ChatOpenAI(model="gpt-4o"),
        browser=browser,
        sensitive_data=sensitive_data
    )
    
    # Run the browser agent to collect information
    results = await browser_agent.run()
    
    # Extract information from results
    extracted_data = parse_browser_agent_results(results)
    
    # Feed the extracted data to Hekmatica for processing
    research_agent = DeepResearchAgent()
    answer = research_agent.answer_question(
        question=query,
        additional_context=extracted_data
    )
    
    await browser.close()
    return answer

def parse_browser_agent_results(results):
    # Custom parsing logic to extract information from browser agent results
    # This would depend on the specific output format of your browser agent task
    ...
    return parsed_data

# Example usage
async def main():
    query = "What are the environmental impacts of electric vehicles compared to gas vehicles?"
    result = await web_research_task(query)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### Benefits of Integration

Combining browser-use with other AI frameworks offers several advantages:

1. **Enhanced Research Capabilities**: The browser agent can navigate to and extract information from dynamic web content that might be inaccessible to traditional API-based search tools.

2. **Real-time Data Access**: While many research agents rely on pre-trained knowledge cutoffs, browser-use enables access to the latest information through direct web navigation.

3. **Interactive Information Gathering**: The browser agent can interact with forms, login systems, and other interactive elements to access information that requires authentication or specific user actions.

4. **Multi-source Validation**: By combining information from multiple web sources, the integrated system can validate facts across different references.

5. **Format Flexibility**: Browser-use can extract information from various media types (text, images, tables) that might be challenging for traditional data extraction methods.

### Implementation Considerations

When integrating browser-use with other AI frameworks:

1. **Define Clear Task Boundaries**: Clearly define which tasks are handled by browser-use versus other components.

2. **Standardize Data Exchange**: Create well-defined interfaces for how data is passed between browser-use and other components.

3. **Handle Authentication Securely**: Use the sensitive_data parameter to securely pass credentials when needed.

4. **Implement Error Recovery**: Design the integration to handle cases where web navigation fails or data is not available.

5. **Consider Caching**: For frequently accessed information, implement caching to reduce browser interactions.

## Extension Points

The browser-use library is designed to be extensible in several ways:

1. **Custom Actions**: Developers can register custom actions to extend functionality.

2. **Custom Hooks**: Pre and post-step hooks can be added for additional processing.

3. **Output Processing**: Custom output processing for application-specific needs.

4. **Browser Configuration**: Fine-grained control over browser behavior.

5. **System Prompts**: Customizable system prompts for specialized use cases.

## Limitations and Considerations

1. **Security Implications**: Giving an AI control of a browser has security implications; use the security features provided.

2. **Performance**: Browser automation can be resource-intensive, especially with multiple browser instances.

3. **Rate Limits**: Be aware of LLM API rate limits for your provider.

4. **Ethical Use**: Ensure the tool is used ethically and legally.

## Development and Contribution

The project is actively developed and accepts contributions. Key areas for development include:

1. Improving agent memory capabilities
2. Enhancing DOM extraction for complex UIs
3. Supporting workflow templates for common tasks
4. Creating datasets for complex tasks
5. Enhancing user experience with human-in-the-loop execution

## Conclusion

Browser-use provides a powerful foundation for building AI-driven web automation tools. Its flexible architecture allows for a wide range of applications from simple web scraping to complex workflows involving multi-step interactions across multiple websites. 