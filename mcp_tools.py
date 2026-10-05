"""Actual stdio MCP tools: read-only schema-validated prediction and context."""
from mcp.server.fastmcp import FastMCP
from lab import predict, context
mcp = FastMCP('business-decision-context')
@mcp.tool()
def predict_sales(TV: float, radio: float, newspaper: float) -> dict:
    """Prediction in thousands of units; association only, no spending action."""
    return predict({'TV':TV,'radio':radio,'newspaper':newspaper})
@mcp.tool()
def metric_context(metric: str = 'sales') -> list:
    """Resolve typed metric/model/source relationships; unknown metrics rejected."""
    return context(metric)
if __name__=='__main__': mcp.run(transport='stdio')
