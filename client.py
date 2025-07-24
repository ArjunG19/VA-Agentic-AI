import asyncio
from langchain_ollama import OllamaLLM
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context

# Initialize the LLM
llm = OllamaLLM(model="llama3.1:latest")

# MCP client and tools
mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
mcp_tools = McpToolSpec(client=mcp_client)

# System prompt for the agent
SYSTEM_PROMPT = """\
You are an AI assistant for tool calling for a smart TV control.
Work with tools to perform the required actions and ask the user for any missing parameters if required.
"""

# Define async function to get the agent
async def get_agent(tools: McpToolSpec) -> FunctionAgent:
    tools = await tools.to_tool_list_async()
    agent = FunctionAgent(
        name="Agent",
        description="An agent interacting with a smart TV",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    print("Agent returned successfully")
    return agent

# Define async function to handle user messages
async def handle_user_message(
    message_content: str,
    agent: FunctionAgent,
    agent_context: Context,
    verbose: bool = False,
):
    handler = agent.run(message_content, ctx=agent_context)
    print("Agent ran")
    async for event in handler.stream_events():
        if verbose and isinstance(event, ToolCall):
            print(f"Calling tool {event.tool_name} with kwargs {event.tool_kwargs}")
        elif verbose and isinstance(event, ToolCallResult):
            print(f"Tool {event.tool_name} returned {event.tool_output}")
    response = await handler
    return str(response)

# Main runner function
async def main():
    agent = await get_agent(mcp_tools)
    agent_context = Context(agent)
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        print("You:", user_input)
        response = await handle_user_message(user_input, agent, agent_context, verbose=True)
        print("Agent:", response)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())
