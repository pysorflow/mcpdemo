#!/usr/bin/env python3
"""
Ollama MCP Bridge
This script allows you to ask Ollama questions about your products using MCP tools
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any
import psycopg2

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'mcpdb',
    'user': 'mcpuser',
    'password': 'mcppass'
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def search_products(query: str, limit: int = 5) -> str:
    """Search products by title or description"""
    try:
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
            return f"No products found for query: '{query}'"
        
        result = f"Found {len(products)} products for '{query}':\n\n"
        for product in products:
            result += f"• SKU: {product[0]}\n"
            result += f"  Title: {product[1][:60]}{'...' if len(product[1]) > 60 else ''}\n"
            result += f"  Category: {product[2]}\n"
            result += f"  Color/Size: {product[3]} / {product[4]}\n"
            result += f"  Stock: {product[5]} | Price: ${product[6] if product[6] else 'N/A'}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error searching products: {str(e)}"

def filter_products_advanced(filters: dict, ordering: list = None, page: int = 1, page_size: int = 10, search: str = "") -> str:
    """Advanced Django-style filtering with pagination"""
    try:
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
            elif filter_key == "warehouse__exact":
                where_conditions.append("warehouse = %s")
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
        if ordering is None:
            ordering = ["title"]
            
        order_fields = []
        field_mapping = {
            "title": "product_title",
            "category": "category_name",
            "stock": "stock",
            "price": "suggested_price",
            "sku": "sku",
            "color": "color_name",
            "size": "size"
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
        count_query = f"SELECT COUNT(*) FROM products {where_clause}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results
        query = f"""
            SELECT sku, product_title, category_name, color_name, size, stock, suggested_price, warehouse
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
        
        # Format results
        result = f"🔍 Advanced Filter Results (Page {page} of {total_pages}):\n"
        result += f"📈 Total: {total_count} | Showing: {len(products)} items\n\n"
        
        if not products:
            result += "No products found matching the criteria.\n"
        else:
            for i, product in enumerate(products, 1):
                result += f"{i:2d}. SKU: {product[0]}\n"
                result += f"    Title: {product[1][:55]}{'...' if len(product[1]) > 55 else ''}\n"
                result += f"    Category: {product[2]} | Color: {product[3]} | Size: {product[4]}\n"
                result += f"    Stock: {product[5]} | Price: ${product[6] if product[6] else 'N/A'} | Warehouse: {product[7]}\n\n"
        
        # Pagination info
        if total_pages > 1:
            result += f"📄 Page {page} of {total_pages}"
            if page < total_pages:
                result += f" | Next: {page + 1}"
            if page > 1:
                result += f" | Previous: {page - 1}"
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"Error in advanced filtering: {str(e)}"

def get_filter_stats(fields: list = None) -> str:
    """Get statistics for filtering"""
    try:
        if fields is None:
            fields = ["category", "color", "size", "warehouse"]
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        result = "📊 Inventory Statistics:\n\n"
        
        field_mapping = {
            "category": ("category_name", "📁 Categories"),
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
                LIMIT 10
            """)
            
            values = cursor.fetchall()
            
            if values:
                result += f"{display_name}:\n"
                for value, count in values:
                    result += f"  • {value}: {count} products\n"
                result += "\n"
        
        # Add quick stock summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN stock = 0 THEN 1 END) as out_of_stock,
                COUNT(CASE WHEN stock <= 10 THEN 1 END) as very_low,
                COUNT(CASE WHEN stock <= 50 THEN 1 END) as low_stock
            FROM products 
            WHERE stock IS NOT NULL
        """)
        
        stock_stats = cursor.fetchone()
        if stock_stats:
            result += "📦 Stock Summary:\n"
            result += f"  • Total Products: {stock_stats[0]:,}\n"
            result += f"  • Out of Stock: {stock_stats[1]} items\n"
            result += f"  • Very Low (≤10): {stock_stats[2]} items\n"
            result += f"  • Low Stock (≤50): {stock_stats[3]} items\n"
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return f"Error getting filter stats: {str(e)}"

def get_product(sku: str) -> str:
    """Get a specific product by SKU"""
    try:
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
            return f"Product with SKU '{sku}' not found"
        
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
        
        return result
        
    except Exception as e:
        return f"Error getting product: {str(e)}"

def get_categories() -> str:
    """Get list of all product categories"""
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
            return "No categories found"
        
        result = "Product Categories:\n\n"
        current_category = ""
        for category, subcategory, count in categories:
            if category != current_category:
                if current_category != "":
                    result += "\n"
                result += f"📁 {category}\n"
                current_category = category
            result += f"  └── {subcategory}: {count} products\n"
        
        return result
        
    except Exception as e:
        return f"Error getting categories: {str(e)}"

def get_low_stock_products(threshold: int = 50, limit: int = 10) -> str:
    """Get products with low stock"""
    try:
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
            return f"No products found with stock <= {threshold}"
        
        result = f"Low Stock Products (stock <= {threshold}):\n\n"
        for product in products:
            result += f"⚠️ SKU: {product[0]}\n"
            result += f"Title: {product[1][:60]}{'...' if len(product[1]) > 60 else ''}\n"
            result += f"Category: {product[2]}\n"
            result += f"Stock: {product[3]} | Warehouse: {product[4]}\n\n"
        
        return result
        
    except Exception as e:
        return f"Error getting low stock products: {str(e)}"

def get_available_models():
    """Get list of available Ollama models"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]  # First column is model name
                    model_size = line.split()[2] if len(line.split()) >= 3 else "Unknown size"
                    models.append((model_name, model_size))
            return models
        else:
            return []
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

def select_model():
    """Let user select a model from available options"""
    print("🔍 Scanning for available Ollama models...")
    models = get_available_models()
    
    if not models:
        print("❌ No Ollama models found. Please install models first with 'ollama pull <model>'")
        return None
    
    print(f"\n📋 Found {len(models)} available models:")
    print("-" * 60)
    
    for i, (model_name, model_size) in enumerate(models, 1):
        # Add descriptions for known models
        description = ""
        if "qwen" in model_name.lower():
            description = " (Best for NLP & conversations)"
        elif "llama3.1" in model_name.lower() and "8b" in model_name.lower():
            description = " (Good balance & reasoning)"
        elif "llama3.2" in model_name.lower() and "latest" in model_name.lower():
            description = " (Balanced performance)"
        elif "llama3.2" in model_name.lower() and "1b" in model_name.lower():
            description = " (Fastest, lightweight)"
        elif "codellama" in model_name.lower():
            description = " (Code-focused)"
        elif "mistral" in model_name.lower():
            description = " (Efficient & capable)"
        
        print(f"{i:2d}. {model_name:<50} {model_size:>8}{description}")
    
    print("-" * 60)
    
    while True:
        try:
            choice = input(f"\n🎯 Select model (1-{len(models)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return None
            
            model_num = int(choice)
            if 1 <= model_num <= len(models):
                selected_model = models[model_num - 1][0]
                print(f"✅ Selected: {selected_model}")
                return selected_model
            else:
                print(f"❌ Please enter a number between 1 and {len(models)}")
                
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return None

def ask_ollama(question: str, model: str = "hf.co/lmstudio-community/Qwen2.5-7B-Instruct-1M-GGUF:Q8_0") -> str:
    """Ask Ollama a question"""
    try:
        result = subprocess.run(
            ["ollama", "run", model, question],
            capture_output=True,
            text=True,
            timeout=60  # Increased timeout for larger model
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Ollama request timed out"
    except Exception as e:
        return f"Error asking Ollama: {str(e)}"

def process_user_question(user_question: str, model: str) -> str:
    """Process user question by determining what data to fetch and asking Ollama"""
    
    # Enhanced rule-based detection with better patterns
    user_lower = user_question.lower()
    import re
    
    print(f"🔍 Analyzing: '{user_question}'")
    
    # Check for SKU patterns (more flexible)
    sku_patterns = [
        r'sku\s*(\w+)',           # "sku 120715"
        r'product\s*(\w+)',       # "product 120715" 
        r'item\s*(\w+)',          # "item 120715"
        r'code\s*(\w+)',          # "code 120715"
        r'\b(\d{5,})\b',          # Any 5+ digit number (likely SKU)
        r'details?\s+of\s+(\w+)', # "details of 120715"
        r'about\s+(\w+)',         # "about 120715"
        r'tell\s+me\s+about\s+(\w+)', # "tell me about 120715"
    ]
    
    # Try to find SKU
    found_sku = None
    for pattern in sku_patterns:
        match = re.search(pattern, user_lower)
        if match:
            potential_sku = match.group(1)
            # Check if it looks like a valid SKU (numbers, letters, reasonable length)
            if re.match(r'^[a-zA-Z0-9]{3,20}$', potential_sku):
                found_sku = potential_sku
                break
    
    # Detect advanced filtering needs
    advanced_filter_indicators = [
        'filter', 'where', 'with', 'having', 'between', 'under', 'over', 'more than', 'less than',
        'greater than', 'cheaper than', 'expensive', 'price range', 'size', 'warehouse', 'sort by'
    ]
    
    # Detect pagination needs
    pagination_indicators = ['page', 'next', 'more', 'show me more', 'continue', 'list']
    
    # Detect statistical queries
    stats_indicators = ['statistics', 'stats', 'breakdown', 'summary', 'overview', 'how many', 'distribution']
    
    # Determine command type
    if found_sku:
        command = f"SKU:{found_sku}"
        
    elif any(indicator in user_lower for indicator in stats_indicators):
        command = "STATS"
        
    elif any(indicator in user_lower for indicator in advanced_filter_indicators):
        # This is a complex filtering query - let LLM parse it
        command = "ADVANCED_FILTER"
        
    elif any(word in user_lower for word in ['categor', 'type', 'kind', 'what do you sell', 'what products']):
        command = "CATEGORIES"
        
    elif any(phrase in user_lower for phrase in ['low stock', 'running low', 'out of stock', 'inventory low', 'stock level']):
        command = "LOW_STOCK"
        
    elif any(word in user_lower for word in ['shirt', 'tshirt', 't-shirt', 'polo', 'hoodie', 'jacket', 'pants', 'jeans', 'dress', 'shoes', 'electronics', 'phone', 'laptop', 'computer']):
        # Extract the main product type
        product_keywords = ['shirt', 'tshirt', 't-shirt', 'polo', 'hoodie', 'jacket', 'pants', 'jeans', 'dress', 'shoes', 'electronics', 'phone', 'laptop', 'computer', 'watch', 'bag', 'backpack']
        for keyword in product_keywords:
            if keyword in user_lower:
                command = f"SEARCH:{keyword}"
                break
        else:
            command = "SEARCH:products"
    else:
        # Use LLM to analyze complex cases
        command = "LLM_ANALYSIS"
    
    print(f"🎯 Initial classification: {command}")
    
    # Execute the appropriate action
    context_data = ""
    
    if command.startswith("SKU:"):
        sku = command.replace("SKU:", "").strip()
        context_data = get_product(sku)
        
    elif command == "STATS":
        context_data = get_filter_stats(["category", "color", "size", "warehouse"])
        
    elif command == "CATEGORIES":
        context_data = get_categories()
        
    elif command == "LOW_STOCK":
        context_data = get_low_stock_products(threshold=50, limit=15)
        
    elif command.startswith("SEARCH:"):
        keyword = command.replace("SEARCH:", "").strip()
        context_data = search_products(keyword, limit=8)
        
    elif command == "ADVANCED_FILTER":
        # Use LLM to parse the filtering requirements
        filter_analysis_prompt = f"""
        Parse this product filtering request: "{user_question}"
        
        Extract filtering criteria and respond with a JSON object containing:
        - filters: object with Django-style filters (category__icontains, stock__gte, price__lte, etc.)
        - ordering: array of sort fields (use "-" prefix for descending)
        - page_size: number of items to show (default 10)
        - search: global search term if mentioned
        
        Examples:
        "Show me blue shirts under $20 with good stock" →
        {{"filters": {{"color__icontains": "blue", "category__icontains": "shirt", "price__lte": 20, "stock__gte": 50}}, "ordering": ["-stock"], "page_size": 10}}
        
        "Find size XL products sorted by price" →
        {{"filters": {{"size__exact": "XL"}}, "ordering": ["price"], "page_size": 10}}
        
        Respond only with the JSON object:"""
        
        llm_response = ask_ollama(filter_analysis_prompt, model).strip()
        print(f"🤖 LLM filter analysis: {llm_response}")
        
        try:
            import json
            filter_config = json.loads(llm_response)
            
            filters = filter_config.get("filters", {})
            ordering = filter_config.get("ordering", ["title"])
            page_size = filter_config.get("page_size", 10)
            search = filter_config.get("search", "")
            
            if filters or search:
                context_data = filter_products_advanced(filters, ordering, 1, page_size, search)
            else:
                # Fallback to simple search
                context_data = search_products(user_question, limit=8)
                
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ LLM filter parsing failed: {e}, falling back to search")
            context_data = search_products(user_question, limit=8)
            
    elif command == "LLM_ANALYSIS":
        # Let LLM decide what to do
        analysis_prompt = f"""
        Analyze this customer question: "{user_question}"
        
        Determine what product data to fetch. Reply with EXACTLY ONE command:
        
        SKU:number - if asking about specific product code/SKU/item number
        SEARCH:keyword - if searching for product types (shirts, electronics, etc.)
        CATEGORIES - if asking about product types/categories available
        LOW_STOCK - if asking about low inventory/out of stock items
        STATS - if asking for statistics, breakdowns, or summaries
        FILTER:keyword - if complex filtering is needed
        GENERAL - if general question not needing specific product data
        
        Examples:
        "show me shirts" → SEARCH:shirts  
        "what's SKU 123?" → SKU:123
        "low stock items" → LOW_STOCK
        "what do you sell" → CATEGORIES
        "give me statistics" → STATS
        "blue shirts under $20" → FILTER:blue shirts price
        
        Reply with just the command:"""
        
        llm_command = ask_ollama(analysis_prompt, model).strip()
        print(f"🤖 LLM command: {llm_command}")
        
        if llm_command.startswith("SEARCH:"):
            keyword = llm_command.replace("SEARCH:", "").strip()
            context_data = search_products(keyword, limit=8)
        elif llm_command == "CATEGORIES":
            context_data = get_categories()
        elif llm_command == "LOW_STOCK":
            context_data = get_low_stock_products(threshold=50, limit=15)
        elif llm_command == "STATS":
            context_data = get_filter_stats(["category", "color", "size", "warehouse"])
        elif llm_command.startswith("SKU:"):
            sku = llm_command.replace("SKU:", "").strip()
            context_data = get_product(sku)
        elif llm_command.startswith("FILTER:"):
            # Try advanced filtering
            context_data = search_products(user_question, limit=8)
        else:
            context_data = "No specific product data needed."
    
    else:
        # Fallback to search
        context_data = search_products(user_question, limit=5)
    
    print(f"📊 Data retrieved: {len(context_data)} characters")
    
    # Enhanced final prompt for better responses
    final_prompt = f"""
    You are a helpful product assistant for an e-commerce inventory system. A customer asked: "{user_question}"
    
    Here's the relevant product data from our inventory:
    {context_data}
    
    Instructions:
    - Answer the customer's question directly and helpfully
    - Use the actual product data provided
    - If products are found, highlight the best matches
    - Include relevant details like SKUs, prices, stock levels when helpful
    - If no products found, suggest alternatives or related items
    - Be conversational and customer-friendly
    - For filtering results, explain what criteria were applied
    - For statistical data, provide insights and recommendations
    
    Customer question: {user_question}
    """
    
    return ask_ollama(final_prompt, model)

def main():
    """Main interactive loop"""
    print("🤖 Ollama + MCP Product Assistant")
    print("Ask me questions about your products!")
    print("=" * 60)
    
    # Let user select a model
    selected_model = select_model()
    if not selected_model:
        print("👋 Goodbye!")
        return
    
    current_model = selected_model
    
    print(f"\n🚀 Starting assistant with model: {selected_model}")
    print("\n📋 Available Commands:")
    print("  - Ask natural language questions about products")
    print("  - 'models' - show and select different model") 
    print("  - 'stats' - show inventory statistics")
    print("  - 'examples' - show example queries")
    print("  - 'quit' or 'q' - exit")
    
    print("\n💡 New Advanced Features:")
    print("  ✅ Django-style filtering (price ranges, stock levels, etc.)")
    print("  ✅ Smart pagination for large result sets")
    print("  ✅ Advanced statistics and breakdowns")
    print("  ✅ Multi-criteria filtering (size, color, warehouse, etc.)")
    
    print("=" * 60)
    
    while True:
        try:
            user_input = input(f"\n💬 Your question [{current_model.split('/')[-1] if '/' in current_model else current_model}]: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == 'models':
                print("\n" + "=" * 60)
                new_model = select_model()
                if new_model:
                    current_model = new_model
                    print(f"🔄 Switched to: {new_model}")
                else:
                    print("🔄 Keeping current model")
                print("=" * 60)
                continue
            
            if user_input.lower() == 'stats':
                print("🔄 Getting inventory statistics...")
                stats_result = get_filter_stats(["category", "color", "size", "warehouse", "status"])
                print(f"\n📊 Inventory Overview:\n{stats_result}")
                continue
                
            if user_input.lower() == 'examples':
                print("\n📝 Example Queries:")
                print("  • 'Show me blue shirts under $20 with good stock'")
                print("  • 'Find size XL products sorted by price'")
                print("  • 'What black items do we have from Gildan warehouse?'")
                print("  • 'Give me details of SKU 120715'")
                print("  • 'Products with more than 1000 units in stock'")
                print("  • 'Show me our most expensive items that are running low'")
                print("  • 'What categories do we sell?'")
                print("  • 'Filter polo shirts with prices between $15 and $30'")
                continue
                
            if not user_input:
                continue
            
            print("🔄 Processing...")
            response = process_user_question(user_input, current_model)
            print(f"\n🤖 Answer:\n{response}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
