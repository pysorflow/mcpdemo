#!/usr/bin/env python3
"""
Product Management MCP Server
This is the main MCP server that provides product management tools
"""

import asyncio
import logging
import os
import psycopg2
from typing import Any, Sequence, Optional
from decimal import Decimal

# MCP imports
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'mcpdb'),
    'user': os.getenv('DB_USER', 'mcpuser'),
    'password': os.getenv('DB_PASSWORD', 'mcppass')
}

server = Server("product-manager")

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="get_product",
            description="Get a specific product by SKU",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU"
                    }
                },
                "required": ["sku"]
            }
        ),
        types.Tool(
            name="list_products",
            description="List all products with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of products to return",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="update_stock",
            description="Update product stock",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU"
                    },
                    "stock": {
                        "type": "integer",
                        "description": "New stock amount"
                    }
                },
                "required": ["sku", "stock"]
            }
        ),
        types.Tool(
            name="search_products",
            description="Search products by title or description",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="advanced_search_products",
            description="Advanced search across all product fields including SKU, title, description, category, color, size, style, warehouse, and status",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - will search across all product fields"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 15
                    },
                    "min_stock": {
                        "type": "integer",
                        "description": "Minimum stock level (optional filter)",
                        "default": 0
                    },
                    "category_filter": {
                        "type": "string",
                        "description": "Filter by category (optional)"
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort results by: title, stock, price, category",
                        "default": "title"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_categories",
            description="Get list of all product categories",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_low_stock_products",
            description="Get products with low stock",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "Stock threshold (default: 50)",
                        "default": 50
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of products to return",
                        "default": 20
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="filter_products",
            description="Advanced filtering and pagination for products with Django-style filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Filter conditions",
                        "properties": {
                            "category__icontains": {"type": "string", "description": "Category contains (case insensitive)"},
                            "category__exact": {"type": "string", "description": "Exact category match"},
                            "subcategory__icontains": {"type": "string", "description": "Subcategory contains"},
                            "color__icontains": {"type": "string", "description": "Color contains"},
                            "size__exact": {"type": "string", "description": "Exact size match"},
                            "size__in": {"type": "array", "items": {"type": "string"}, "description": "Size is in list"},
                            "stock__gte": {"type": "integer", "description": "Stock greater than or equal"},
                            "stock__lte": {"type": "integer", "description": "Stock less than or equal"},
                            "stock__gt": {"type": "integer", "description": "Stock greater than"},
                            "stock__lt": {"type": "integer", "description": "Stock less than"},
                            "price__gte": {"type": "number", "description": "Price greater than or equal"},
                            "price__lte": {"type": "number", "description": "Price less than or equal"},
                            "title__icontains": {"type": "string", "description": "Title contains"},
                            "sku__icontains": {"type": "string", "description": "SKU contains"},
                            "warehouse__exact": {"type": "string", "description": "Exact warehouse match"},
                            "status__exact": {"type": "string", "description": "Exact status match"}
                        }
                    },
                    "ordering": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Order by fields. Prefix with '-' for descending (e.g., ['-stock', 'title'])",
                        "default": ["title"]
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of items per page",
                        "default": 20
                    },
                    "search": {
                        "type": "string",
                        "description": "Global search across multiple fields"
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Handle tool calls"""
    
    if name == "get_product":
        try:
            sku = arguments.get("sku", "")
            if not sku:
                return [types.TextContent(type="text", text="SKU is required")]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT style, sku, product_title, product_description, category_name, 
                       subcategory_name, color_name, size, stock, suggested_price, 
                       warehouse, product_status
                FROM products 
                WHERE sku = %s
            """, (sku,))
            
            product = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not product:
                return [types.TextContent(type="text", text=f"Product with SKU '{sku}' not found")]
            
            result = f"""Product Details:
SKU: {product[1]}
Style: {product[0]}
Title: {product[2]}
Description: {product[3][:200]}{'...' if len(product[3]) > 200 else ''}
Category: {product[4]} > {product[5]}
Color: {product[6]}
Size: {product[7]}
Stock: {product[8]}
Price: ${product[9] if product[9] else 'N/A'}
Warehouse: {product[10]}
Status: {product[11]}"""
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error getting product: {str(e)}")]
    
    elif name == "list_products":
        try:
            category = arguments.get("category", "")
            limit = arguments.get("limit", 10)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if category:
                cursor.execute("""
                    SELECT sku, product_title, category_name, color_name, size, stock, suggested_price
                    FROM products 
                    WHERE category_name ILIKE %s
                    ORDER BY product_title
                    LIMIT %s
                """, (f"%{category}%", limit))
            else:
                cursor.execute("""
                    SELECT sku, product_title, category_name, color_name, size, stock, suggested_price
                    FROM products 
                    ORDER BY product_title
                    LIMIT %s
                """, (limit,))
            
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not products:
                return [types.TextContent(type="text", text="No products found")]
            
            result = f"Products ({len(products)} found):\n\n"
            for product in products:
                result += f"SKU: {product[0]}\n"
                result += f"Title: {product[1][:60]}{'...' if len(product[1]) > 60 else ''}\n"
                result += f"Category: {product[2]}\n"
                result += f"Color/Size: {product[3]} / {product[4]}\n"
                result += f"Stock: {product[5]} | Price: ${product[6] if product[6] else 'N/A'}\n"
                result += "-" * 50 + "\n"
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error listing products: {str(e)}")]
    
    elif name == "update_stock":
        try:
            sku = arguments.get("sku", "")
            stock = arguments.get("stock")
            
            if not sku:
                return [types.TextContent(type="text", text="SKU is required")]
            if stock is None:
                return [types.TextContent(type="text", text="Stock amount is required")]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if product exists
            cursor.execute("SELECT product_title FROM products WHERE sku = %s", (sku,))
            product = cursor.fetchone()
            
            if not product:
                cursor.close()
                conn.close()
                return [types.TextContent(type="text", text=f"Product with SKU '{sku}' not found")]
            
            # Update stock
            cursor.execute("""
                UPDATE products 
                SET stock = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE sku = %s
            """, (stock, sku))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return [types.TextContent(type="text", text=f"Stock updated successfully for '{product[0]}' (SKU: {sku}). New stock: {stock}")]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error updating stock: {str(e)}")]
    
    elif name == "search_products":
        try:
            query = arguments.get("query", "")
            limit = arguments.get("limit", 10)
            
            if not query:
                return [types.TextContent(type="text", text="Search query is required")]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Enhanced search across more fields
            cursor.execute("""
                SELECT sku, product_title, category_name, color_name, size, stock, suggested_price
                FROM products 
                WHERE product_title ILIKE %s 
                   OR product_description ILIKE %s
                   OR sku ILIKE %s
                   OR category_name ILIKE %s
                   OR color_name ILIKE %s
                   OR subcategory_name ILIKE %s
                ORDER BY 
                    CASE 
                        WHEN sku ILIKE %s THEN 1
                        WHEN product_title ILIKE %s THEN 2
                        WHEN category_name ILIKE %s THEN 3
                        ELSE 4
                    END,
                    product_title
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%",
                  f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not products:
                return [types.TextContent(type="text", text=f"No products found for query: '{query}'")]
            
            result = f"🔍 Search Results for '{query}' ({len(products)} found):\n\n"
            for product in products:
                result += f"🏷️  SKU: {product[0]}\n"
                result += f"📋 Title: {product[1][:65]}{'...' if len(product[1]) > 65 else ''}\n"
                result += f"📂 Category: {product[2]}\n"
                result += f"🎨 Color/Size: {product[3]} / {product[4]}\n"
                result += f"📦 Stock: {product[5]} | 💰 Price: ${product[6] if product[6] else 'N/A'}\n"
                result += "-" * 60 + "\n"
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error searching products: {str(e)}")]
    
    elif name == "advanced_search_products":
        try:
            query = arguments.get("query", "")
            limit = arguments.get("limit", 15)
            min_stock = arguments.get("min_stock", 0)
            category_filter = arguments.get("category_filter", "")
            sort_by = arguments.get("sort_by", "title")
            
            if not query:
                return [types.TextContent(type="text", text="Search query is required")]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Build comprehensive search query across all fields
            search_conditions = []
            search_params = []
            
            # Search across multiple fields
            search_fields = [
                "sku", "style", "product_title", "product_description", 
                "category_name", "subcategory_name", "color_name", 
                "size", "warehouse", "product_status"
            ]
            
            field_conditions = " OR ".join([f"{field} ILIKE %s" for field in search_fields])
            search_conditions.append(f"({field_conditions})")
            search_params.extend([f"%{query}%" for _ in search_fields])
            
            # Add stock filter
            if min_stock > 0:
                search_conditions.append("stock >= %s")
                search_params.append(min_stock)
            
            # Add category filter
            if category_filter:
                search_conditions.append("category_name ILIKE %s")
                search_params.append(f"%{category_filter}%")
            
            # Determine sort order
            sort_mapping = {
                "title": "product_title",
                "stock": "stock DESC",
                "price": "suggested_price DESC NULLS LAST",
                "category": "category_name, product_title"
            }
            order_by = sort_mapping.get(sort_by, "product_title")
            
            # Build final query
            where_clause = " AND ".join(search_conditions)
            
            sql_query = f"""
                SELECT style, sku, product_title, product_description, category_name, 
                       subcategory_name, color_name, size, stock, suggested_price, 
                       warehouse, product_status
                FROM products 
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT %s
            """
            
            search_params.append(limit)
            cursor.execute(sql_query, search_params)
            
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not products:
                return [types.TextContent(type="text", text=f"No products found for advanced search: '{query}'")]
            
            result = f"🔍 Advanced Search Results for '{query}' ({len(products)} found):\n"
            if category_filter:
                result += f"📁 Category Filter: {category_filter}\n"
            if min_stock > 0:
                result += f"📦 Min Stock: {min_stock}\n"
            result += f"🔤 Sorted by: {sort_by}\n\n"
            
            for product in products:
                result += f"🏷️  SKU: {product[1]} | Style: {product[0]}\n"
                result += f"📋 Title: {product[2][:70]}{'...' if len(product[2]) > 70 else ''}\n"
                result += f"📂 Category: {product[4]} > {product[5]}\n"
                result += f"🎨 Color: {product[6]} | Size: {product[7]}\n"
                result += f"📦 Stock: {product[8]} | 💰 Price: ${product[9] if product[9] else 'N/A'}\n"
                result += f"🏪 Warehouse: {product[10]} | Status: {product[11]}\n"
                if product[3]:  # Description
                    result += f"📝 Description: {product[3][:100]}{'...' if len(product[3]) > 100 else ''}\n"
                result += "─" * 80 + "\n"
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error in advanced search: {str(e)}")]
    
    elif name == "get_categories":
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category_name, subcategory_name, COUNT(*) as product_count
                FROM products 
                WHERE category_name != '' 
                GROUP BY category_name, subcategory_name
                ORDER BY category_name, subcategory_name
            """)
            
            categories = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not categories:
                return [types.TextContent(type="text", text="No categories found")]
            
            result = "Product Categories:\n\n"
            current_category = ""
            for category, subcategory, count in categories:
                if category != current_category:
                    if current_category != "":
                        result += "\n"
                    result += f"📁 {category}\n"
                    current_category = category
                result += f"  └── {subcategory}: {count} products\n"
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error getting categories: {str(e)}")]
    
    elif name == "get_low_stock_products":
        try:
            threshold = arguments.get("threshold", 50)
            limit = arguments.get("limit", 20)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sku, product_title, category_name, stock, warehouse
                FROM products 
                WHERE stock IS NOT NULL AND stock <= %s
                ORDER BY stock ASC
                LIMIT %s
            """, (threshold, limit))
            
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not products:
                return [types.TextContent(type="text", text=f"No products found with stock <= {threshold}")]
            
            result = f"Low Stock Products (stock <= {threshold}):\n\n"
            for product in products:
                result += f"⚠️ SKU: {product[0]}\n"
                result += f"Title: {product[1][:60]}{'...' if len(product[1]) > 60 else ''}\n"
                result += f"Category: {product[2]}\n"
                result += f"Stock: {product[3]} | Warehouse: {product[4]}\n"
                result += "-" * 50 + "\n"
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error getting low stock products: {str(e)}")]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main function to run the MCP server"""
    # Use stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="product-manager",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
