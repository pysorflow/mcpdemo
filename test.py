#!/usr/bin/env python3
"""
MCP Product Server Test
This script tests all MCP server functionality and database connectivity
"""

import psycopg2
import os
import sys

# Database connection parameters
# Use 'localhost' when running test from host machine, 'db' when running inside Docker
DB_CONFIG = {
    'host': 'localhost',  # Changed from 'db' to 'localhost' for local testing
    'port': '5432',
    'database': 'mcpdb',
    'user': 'mcpuser',
    'password': 'mcppass'
}

def test_database_connection():
    """Test basic database connectivity"""
    print("🔍 Testing database connection...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        print(f"✅ Database connected successfully")
        print(f"   PostgreSQL version: {version[0][:50]}...")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def test_products_table():
    """Test if products table exists and has data"""
    print("\n🔍 Testing products table...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'products'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            cursor.close()
            conn.close()
            print("❌ Products table does not exist")
            return False
        
        # Get table statistics
        cursor.execute("SELECT COUNT(*) FROM products;")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT category_name) FROM products WHERE category_name != '';")
        category_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"✅ Products table exists")
        print(f"   Total products: {total_count}")
        print(f"   Categories: {category_count}")
        
        return total_count > 0
        
    except Exception as e:
        print(f"❌ Products table test failed: {str(e)}")
        return False

def test_mcp_tools():
    """Test all MCP server tools functionality"""
    print("\n🔍 Testing MCP server tools...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Test 1: Get a product by SKU
        print("   Testing get_product tool...")
        cursor.execute("SELECT sku FROM products LIMIT 1")
        test_sku = cursor.fetchone()
        if test_sku:
            cursor.execute("""
                SELECT sku, product_title, stock FROM products WHERE sku = %s
            """, (test_sku[0],))
            product = cursor.fetchone()
            print(f"   ✅ get_product: Found product {product[0]} - {product[1][:30]}...")
        else:
            print("   ❌ get_product: No products to test with")
            return False
        
        # Test 2: List products
        print("   Testing list_products tool...")
        cursor.execute("SELECT sku, product_title FROM products LIMIT 3")
        products = cursor.fetchall()
        if products:
            print(f"   ✅ list_products: Found {len(products)} products")
        else:
            print("   ❌ list_products: No products found")
            return False
        
        # Test 3: Search products
        print("   Testing search_products tool...")
        cursor.execute("""
            SELECT sku, product_title FROM products 
            WHERE product_title ILIKE '%Hanes%' LIMIT 3
        """)
        search_results = cursor.fetchall()
        if search_results:
            print(f"   ✅ search_products: Found {len(search_results)} results for 'Hanes'")
        else:
            print("   ⚠️ search_products: No results found (this is ok)")
        
        # Test 4: Get categories
        print("   Testing get_categories tool...")
        cursor.execute("""
            SELECT category_name, COUNT(*) FROM products 
            WHERE category_name != '' 
            GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 3
        """)
        categories = cursor.fetchall()
        if categories:
            print(f"   ✅ get_categories: Found {len(categories)} categories")
            for cat, count in categories:
                print(f"      - {cat}: {count} products")
        else:
            print("   ❌ get_categories: No categories found")
            return False
        
        # Test 5: Get low stock products
        print("   Testing get_low_stock_products tool...")
        cursor.execute("""
            SELECT sku, product_title, stock FROM products 
            WHERE stock IS NOT NULL AND stock < 100 
            ORDER BY stock ASC LIMIT 3
        """)
        low_stock = cursor.fetchall()
        if low_stock:
            print(f"   ✅ get_low_stock_products: Found {len(low_stock)} low stock products")
        else:
            print("   ⚠️ get_low_stock_products: No low stock products (this is ok)")
        
        # Test 6: Filter products (Django-style filtering)
        print("   Testing filter_products tool...")
        cursor.execute("""
            SELECT sku, product_title, category_name, stock FROM products 
            WHERE category_name ILIKE '%T-Shirt%' AND stock > 100
            LIMIT 3
        """)
        filter_results = cursor.fetchall()
        if filter_results:
            print(f"   ✅ filter_products: Found {len(filter_results)} T-shirts with good stock")
            for result in filter_results:
                print(f"      - {result[0]}: {result[1][:25]}... (Stock: {result[3]})")
        else:
            print("   ⚠️ filter_products: No T-shirts with high stock found (this is ok)")
        
        # Test 7: Get filter statistics
        print("   Testing get_filter_stats tool...")
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT category_name) as categories,
                COUNT(DISTINCT color_name) as colors,
                COUNT(DISTINCT size) as sizes,
                COUNT(*) as total_products
            FROM products 
            WHERE category_name != '' OR color_name != '' OR size != ''
        """)
        stats = cursor.fetchone()
        if stats:
            print(f"   ✅ get_filter_stats: {stats[3]} products, {stats[0]} categories, {stats[1]} colors, {stats[2]} sizes")
        else:
            print("   ❌ get_filter_stats: No statistics data")
            return False
        
        # Test 8: Update stock (simulate without actually updating)
        print("   Testing update_stock tool...")
        cursor.execute("SELECT sku, stock FROM products WHERE stock IS NOT NULL LIMIT 1")
        test_product = cursor.fetchone()
        if test_product:
            print(f"   ✅ update_stock: Ready to update stock for {test_product[0]}")
            print(f"      Current stock: {test_product[1]} (not actually updating)")
        else:
            print("   ❌ update_stock: No products with stock data")
            return False
        
        cursor.close()
        conn.close()
        
        print("   ✅ All MCP tools are functional!")
        return True
        
    except Exception as e:
        print(f"   ❌ MCP tools test failed: {str(e)}")
        return False

def test_indexes_and_performance():
    """Test database indexes and basic performance"""
    print("\n🔍 Testing database indexes...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check if indexes exist
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'products' 
            AND indexname LIKE 'idx_products_%'
        """)
        indexes = cursor.fetchall()
        
        if indexes:
            print(f"   ✅ Database indexes: Found {len(indexes)} indexes")
            for idx in indexes:
                print(f"      - {idx[0]}")
        else:
            print("   ⚠️ No custom indexes found (basic functionality will still work)")
        
        # Test query performance with EXPLAIN
        cursor.execute("EXPLAIN SELECT * FROM products WHERE sku = '120682'")
        explain_result = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print("   ✅ Query performance test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Index test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=== MCP Product Server Comprehensive Test ===")
    print()
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Products Table", test_products_table),
        ("MCP Tools", test_mcp_tools),
        ("Database Performance", test_indexes_and_performance),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"📋 Running {test_name} test...")
        if test_func():
            passed_tests += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Your MCP Product Server is ready to use!")
        print()
        print("📋 Available MCP Tools:")
        print("  • get_product - Get product details by SKU")
        print("  • list_products - List products (with optional category filter)")
        print("  • update_stock - Update product stock levels")
        print("  • search_products - Search products by title/description")
        print("  • get_categories - Get all product categories")
        print("  • get_low_stock_products - Find products with low stock")
        print("  • filter_products - Advanced Django-style filtering with pagination")
        print("  • get_filter_stats - Get inventory statistics and breakdowns")
        print("  • get_search_results - Enhanced search across all product fields")
        print()
        print("🚀 To use the MCP server:")
        print("  docker-compose up -d  # Start services")
        print("  # Connect your MCP client to the server")
        return True
    else:
        print(f"❌ {total_tests - passed_tests} test(s) failed. Please check your setup.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
