"""Integration test uses a real stdio MCP session and calls both actual tools."""
import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    params=StdioServerParameters(command=sys.executable,args=[str(Path(__file__).parent/'mcp_tools.py')])
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as s:
            await s.initialize(); tools=await s.list_tools()
            assert {x.name for x in tools.tools}=={'predict_sales','metric_context'}
            p=await s.call_tool('predict_sales',{'TV':276.9,'radio':48.9,'newspaper':41.8})
            v=json.loads(p.content[0].text);assert abs(v['prediction']-24.71035127235)<1e-9
            c=await s.call_tool('metric_context',{'metric':'sales'});assert not c.isError
            bad=await s.call_tool('metric_context',{'metric':'unverified_roi'});assert bad.isError
            print('MCP PASS: actual stdio initialization, tool discovery, prediction, context and unknown-metric rejection')
if __name__=='__main__':asyncio.run(main())
