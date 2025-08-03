#!/usr/bin/env python3
"""
Local MCP Server for Inspector
This runs outside Docker but connects to the Docker database
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

# Database connection parameters - connects to Docker database
DB_CONFIG = {
    'host': 'localhost',  # Changed from 'db' to 'localhost'
    'port': '5432',
    'database': 'mcpdb',
    'user': 'mcpuser',
    'password': 'mcppass'
}

server = Server("demo-product-manager")

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
            name="get_filter_stats",
            description="Get statistics for filtering - available values for each filterable field",
            inputSchema={
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to get stats for: category, subcategory, color, size, warehouse, status",
                        "default": ["category", "color", "size"]
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
    
    elif name == "filter_products":
        try:
            filters = arguments.get("filters", {})
            ordering = arguments.get("ordering", ["title"])
            page = arguments.get("page", 1)
            page_size = arguments.get("page_size", 20)
            search = arguments.get("search", "")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Build WHERE conditions
            where_conditions = []
            params = []
            
            # Apply Django-style filters
            for filter_key, filter_value in filters.items():
                if filter_value is None or filter_value == "":
                    continue
                    
                if filter_key == "category__icontains":
                    where_conditions.append("category_name ILIKE %s")
                    params.append(f"%{filter_value}%")
                elif filter_key == "category__exact":
                    where_conditions.append("category_name = %s")
                    params.append(filter_value)
                elif filter_key == "subcategory__icontains":
                    where_conditions.append("subcategory_name ILIKE %s")
                    params.append(f"%{filter_value}%")
                elif filter_key == "color__icontains":
                    where_conditions.append("color_name ILIKE %s")
                    params.append(f"%{filter_value}%")
                elif filter_key == "size__exact":
                    where_conditions.append("size = %s")
                    params.append(filter_value)
                elif filter_key == "size__in":
                    if isinstance(filter_value, list) and filter_value:
                        placeholders = ",".join(["%s"] * len(filter_value))
                        where_conditions.append(f"size IN ({placeholders})")
                        params.extend(filter_value)
                elif filter_key == "stock__gte":
                    where_conditions.append("stock >= %s")
                    params.append(filter_value)
                elif filter_key == "stock__lte":
                    where_conditions.append("stock <= %s")
                    params.append(filter_value)
                elif filter_key == "stock__gt":
                    where_conditions.append("stock > %s")
                    params.append(filter_value)
                elif filter_key == "stock__lt":
                    where_conditions.append("stock < %s")
                    params.append(filter_value)
                elif filter_key == "price__gte":
                    where_conditions.append("suggested_price >= %s")
                    params.append(filter_value)
                elif filter_key == "price__lte":
                    where_conditions.append("suggested_price <= %s")
                    params.append(filter_value)
                elif filter_key == "title__icontains":
                    where_conditions.append("product_title ILIKE %s")
                    params.append(f"%{filter_value}%")
                elif filter_key == "sku__icontains":
                    where_conditions.append("sku ILIKE %s")
                    params.append(f"%{filter_value}%")
                elif filter_key == "warehouse__exact":
                    where_conditions.append("warehouse = %s")
                    params.append(filter_value)
                elif filter_key == "status__exact":
                    where_conditions.append("product_status = %s")
                    params.append(filter_value)
            
            # Global search
            if search:
                search_condition = """(
                    product_title ILIKE %s OR 
                    product_description ILIKE %s OR 
                    sku ILIKE %s OR 
                    category_name ILIKE %s OR 
                    color_name ILIKE %s
                )"""
                where_conditions.append(search_condition)
                search_param = f"%{search}%"
                params.extend([search_param] * 5)
            
            # Build WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Build ORDER BY clause
            order_fields = []
            field_mapping = {
                "title": "product_title",
                "category": "category_name",
                "stock": "stock",
                "price": "suggested_price",
                "sku": "sku",
                "color": "color_name",
                "size": "size",
                "warehouse": "warehouse",
                "status": "product_status"
            }
            
            for field in ordering:
                if field.startswith("-"):
                    field_name = field[1:]
                    direction = "DESC"
                else:
                    field_name = field
                    direction = "ASC"
                
                db_field = field_mapping.get(field_name, field_name)
                order_fields.append(f"{db_field} {direction}")
            
            order_clause = "ORDER BY " + ", ".join(order_fields) if order_fields else "ORDER BY product_title"
            
            # Calculate pagination
            offset = (page - 1) * page_size
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) 
                FROM products 
                {where_clause}
            """
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            query = f"""
                SELECT sku, product_title, category_name, subcategory_name, 
                       color_name, size, stock, suggested_price, warehouse, product_status
                FROM products 
                {where_clause}
                {order_clause}
                LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, params + [page_size, offset])
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            # Format results
            result = f"📊 Filtered Products (Page {page} of {total_pages}):\n"
            result += f"📈 Total Results: {total_count} | Showing: {len(products)} items\n"
            result += f"📄 Page Size: {page_size}\n"
            
            if filters:
                result += f"🔍 Active Filters: {', '.join([f'{k}={v}' for k, v in filters.items() if v])}\n"
            if search:
                result += f"🔎 Search: '{search}'\n"
            if ordering != ["title"]:
                result += f"📋 Ordering: {', '.join(ordering)}\n"
            
            result += "=" * 70 + "\n\n"
            
            if not products:
                result += "No products found matching the filters.\n"
            else:
                for i, product in enumerate(products, 1):
                    result += f"{(page-1)*page_size + i:3d}. 🏷️  SKU: {product[0]}\n"
                    result += f"     📋 Title: {product[1][:60]}{'...' if len(product[1]) > 60 else ''}\n"
                    result += f"     📂 Category: {product[2]} > {product[3]}\n"
                    result += f"     🎨 Color: {product[4]} | Size: {product[5]}\n"
                    result += f"     📦 Stock: {product[6]} | 💰 Price: ${product[7] if product[7] else 'N/A'}\n"
                    result += f"     🏪 Warehouse: {product[8]} | Status: {product[9]}\n"
                    result += "-" * 70 + "\n"
            
            # Pagination info
            result += f"\n📄 Pagination:\n"
            result += f"   Current Page: {page} of {total_pages}\n"
            result += f"   Items: {offset + 1}-{min(offset + page_size, total_count)} of {total_count}\n"
            if has_previous:
                result += f"   ← Previous: Page {page - 1}\n"
            if has_next:
                result += f"   → Next: Page {page + 1}\n"
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error filtering products: {str(e)}")]
    
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
    
    elif name == "get_filter_stats":
        try:
            fields = arguments.get("fields", ["category", "color", "size"])
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            result = "📊 Filter Statistics:\n\n"
            
            field_mapping = {
                "category": ("category_name", "📁 Categories"),
                "subcategory": ("subcategory_name", "📂 Subcategories"),
                "color": ("color_name", "🎨 Colors"),
                "size": ("size", "📏 Sizes"),
                "warehouse": ("warehouse", "🏪 Warehouses"),
                "status": ("product_status", "📋 Status")
            }
            
            for field in fields:
                if field not in field_mapping:
                    continue
                    
                db_field, display_name = field_mapping[field]
                
                cursor.execute(f"""
                    SELECT {db_field}, COUNT(*) as count
                    FROM products 
                    WHERE {db_field} IS NOT NULL AND {db_field} != ''
                    GROUP BY {db_field}
                    ORDER BY count DESC, {db_field}
                """)
                
                values = cursor.fetchall()
                
                if values:
                    result += f"{display_name} ({len(values)} unique values):\n"
                    for value, count in values[:15]:  # Show top 15
                        result += f"  • {value}: {count} products\n"
                    
                    if len(values) > 15:
                        result += f"  ... and {len(values) - 15} more\n"
                    result += "\n"
            
            # Add stock statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_products,
                    MIN(stock) as min_stock,
                    MAX(stock) as max_stock,
                    AVG(stock) as avg_stock,
                    COUNT(CASE WHEN stock = 0 THEN 1 END) as out_of_stock,
                    COUNT(CASE WHEN stock <= 10 THEN 1 END) as low_stock_10,
                    COUNT(CASE WHEN stock <= 50 THEN 1 END) as low_stock_50
                FROM products 
                WHERE stock IS NOT NULL
            """)
            
            stock_stats = cursor.fetchone()
            if stock_stats:
                result += "📦 Stock Statistics:\n"
                result += f"  • Total Products: {stock_stats[0]:,}\n"
                result += f"  • Stock Range: {stock_stats[1]} - {stock_stats[2]:,}\n"
                result += f"  • Average Stock: {stock_stats[3]:.1f}\n"
                result += f"  • Out of Stock: {stock_stats[4]} products\n"
                result += f"  • Low Stock (≤10): {stock_stats[5]} products\n"
                result += f"  • Low Stock (≤50): {stock_stats[6]} products\n\n"
            
            # Add price statistics
            cursor.execute("""
                SELECT 
                    MIN(suggested_price) as min_price,
                    MAX(suggested_price) as max_price,
                    AVG(suggested_price) as avg_price,
                    COUNT(CASE WHEN suggested_price IS NOT NULL THEN 1 END) as priced_products
                FROM products 
                WHERE suggested_price IS NOT NULL
            """)
            
            price_stats = cursor.fetchone()
            if price_stats and price_stats[3] > 0:
                result += "💰 Price Statistics:\n"
                result += f"  • Price Range: ${price_stats[0]:.2f} - ${price_stats[1]:.2f}\n"
                result += f"  • Average Price: ${price_stats[2]:.2f}\n"
                result += f"  • Products with Prices: {price_stats[3]:,}\n"
            
            cursor.close()
            conn.close()
            
            return [types.TextContent(type="text", text=result)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error getting filter stats: {str(e)}")]
    
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
