#!/usr/bin/env python3
"""
Product CSV Import Script
This script imports product data from CSV into the PostgreSQL database
"""

import csv
import psycopg2
import os
import sys
import html
from decimal import Decimal, InvalidOperation
from datetime import datetime

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'mcpdb'),
    'user': os.getenv('DB_USER', 'mcpuser'),
    'password': os.getenv('DB_PASSWORD', 'mcppass')
}

def clean_html_entities(text):
    """Clean HTML entities from text"""
    if not text:
        return text
    return html.unescape(text)

def safe_decimal(value, default=None):
    """Safely convert string to Decimal"""
    if not value or value.strip() == '':
        return default
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return default

def safe_int(value, default=None):
    """Safely convert string to integer"""
    if not value or value.strip() == '':
        return default
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default

def create_database_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def create_products_table(conn):
    """Create the products table with all necessary indexes and triggers"""
    try:
        cursor = conn.cursor()
        
        # Create products table
        create_table_sql = """
        -- Create products table based on the CSV structure
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            style VARCHAR(20),
            sku VARCHAR(32) UNIQUE NOT NULL,
            product_title VARCHAR(255),
            product_description TEXT,
            available_sizes VARCHAR(128),
            suggested_price DECIMAL(10, 2),
            category_name VARCHAR(100),
            subcategory_name VARCHAR(100),
            color_name VARCHAR(50),
            size VARCHAR(16),
            stock INTEGER,
            piece_weight DECIMAL(8, 4),
            warehouse VARCHAR(64),
            product_status VARCHAR(32),
            msrp DECIMAL(10, 2),
            map_pricing DECIMAL(10, 2),
            front_model_image_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create indexes for better query performance
        create_indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_products_style ON products(style);
        CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_name);
        CREATE INDEX IF NOT EXISTS idx_products_subcategory ON products(subcategory_name);
        CREATE INDEX IF NOT EXISTS idx_products_color ON products(color_name);
        CREATE INDEX IF NOT EXISTS idx_products_size ON products(size);
        CREATE INDEX IF NOT EXISTS idx_products_warehouse ON products(warehouse);
        CREATE INDEX IF NOT EXISTS idx_products_status ON products(product_status);
        """
        
        # Create function to update the updated_at timestamp
        create_function_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language plpgsql;
        """
        
        # Create trigger to automatically update updated_at
        create_trigger_sql = """
        DROP TRIGGER IF EXISTS update_products_updated_at ON products;
        CREATE TRIGGER update_products_updated_at
            BEFORE UPDATE ON products
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        # Execute all SQL statements
        cursor.execute(create_table_sql)
        cursor.execute(create_indexes_sql)
        cursor.execute(create_function_sql)
        cursor.execute(create_trigger_sql)
        
        conn.commit()
        cursor.close()
        print("✅ Products table created successfully with indexes and triggers")
        return True
    except Exception as e:
        print(f"❌ Failed to create products table: {e}")
        conn.rollback()
        return False

def import_csv_data(conn, csv_file_path, batch_size=1000):
    """Import data from CSV file to products table"""
    try:
        cursor = conn.cursor()
        
        # Prepare the INSERT statement
        insert_sql = """
        INSERT INTO products (
            style, sku, product_title, product_description, available_sizes,
            suggested_price, category_name, subcategory_name, color_name, size,
            stock, piece_weight, warehouse, product_status, msrp, map_pricing,
            front_model_image_url
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) ON CONFLICT (sku) DO UPDATE SET
            style = EXCLUDED.style,
            product_title = EXCLUDED.product_title,
            product_description = EXCLUDED.product_description,
            available_sizes = EXCLUDED.available_sizes,
            suggested_price = EXCLUDED.suggested_price,
            category_name = EXCLUDED.category_name,
            subcategory_name = EXCLUDED.subcategory_name,
            color_name = EXCLUDED.color_name,
            size = EXCLUDED.size,
            stock = EXCLUDED.stock,
            piece_weight = EXCLUDED.piece_weight,
            warehouse = EXCLUDED.warehouse,
            product_status = EXCLUDED.product_status,
            msrp = EXCLUDED.msrp,
            map_pricing = EXCLUDED.map_pricing,
            front_model_image_url = EXCLUDED.front_model_image_url,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        batch_data = []
        total_rows = 0
        processed_rows = 0
        error_rows = 0
        
        print(f"📁 Opening CSV file: {csv_file_path}")
        
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            # Count total rows first
            total_rows = sum(1 for line in csvfile) - 1  # Subtract header
            csvfile.seek(0)  # Reset file pointer
            
            reader = csv.DictReader(csvfile)
            
            print(f"📊 Total rows to process: {total_rows}")
            print("🔄 Starting import...")
            
            for row_num, row in enumerate(reader, 1):
                try:
                    # Clean and prepare data
                    data = (
                        clean_html_entities(row.get('style', '')),
                        row.get('sku', ''),  # SKU is required
                        clean_html_entities(row.get('product_title', '')),
                        clean_html_entities(row.get('product_description', '')),
                        clean_html_entities(row.get('available_sizes', '')),
                        safe_decimal(row.get('suggested_price')),
                        clean_html_entities(row.get('category_name', '')),
                        clean_html_entities(row.get('subcategory_name', '')),
                        clean_html_entities(row.get('color_name', '')),
                        clean_html_entities(row.get('size', '')),
                        safe_int(row.get('stock')),
                        safe_decimal(row.get('piece_weight')),
                        clean_html_entities(row.get('warehouse', '')),
                        clean_html_entities(row.get('product_status', '')),
                        safe_decimal(row.get('msrp')),
                        safe_decimal(row.get('map_pricing')),
                        row.get('front_model_image_url', '')
                    )
                    
                    # Skip rows with empty SKU
                    if not data[1]:
                        error_rows += 1
                        continue
                    
                    batch_data.append(data)
                    
                    # Process batch when it reaches batch_size
                    if len(batch_data) >= batch_size:
                        cursor.executemany(insert_sql, batch_data)
                        conn.commit()
                        processed_rows += len(batch_data)
                        print(f"✅ Processed {processed_rows}/{total_rows} rows ({processed_rows/total_rows*100:.1f}%)")
                        batch_data = []
                
                except Exception as e:
                    error_rows += 1
                    print(f"⚠️ Error processing row {row_num}: {e}")
                    continue
            
            # Process remaining batch
            if batch_data:
                cursor.executemany(insert_sql, batch_data)
                conn.commit()
                processed_rows += len(batch_data)
            
            cursor.close()
            
            print(f"\n🎉 Import completed!")
            print(f"✅ Successfully processed: {processed_rows} rows")
            print(f"❌ Errors: {error_rows} rows")
            print(f"📊 Success rate: {processed_rows/(processed_rows+error_rows)*100:.1f}%")
            
            return processed_rows, error_rows
            
    except Exception as e:
        print(f"❌ Failed to import CSV data: {e}")
        conn.rollback()
        return 0, 0

def get_table_stats(conn):
    """Get statistics about the products table"""
    try:
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM products;")
        total_count = cursor.fetchone()[0]
        
        # Get sample records
        cursor.execute("SELECT style, sku, product_title, category_name, stock FROM products LIMIT 5;")
        sample_records = cursor.fetchall()
        
        # Get categories count
        cursor.execute("SELECT category_name, COUNT(*) FROM products WHERE category_name != '' GROUP BY category_name ORDER BY COUNT(*) DESC LIMIT 10;")
        categories = cursor.fetchall()
        
        cursor.close()
        
        print(f"\n📊 Database Statistics:")
        print(f"Total products: {total_count}")
        
        print(f"\n📝 Sample records:")
        for record in sample_records:
            print(f"  {record[0]} | {record[1]} | {record[2][:50]}... | {record[3]} | Stock: {record[4]}")
        
        print(f"\n🏷️ Top categories:")
        for category, count in categories:
            print(f"  {category}: {count} products")
            
    except Exception as e:
        print(f"❌ Failed to get table statistics: {e}")

def main():
    """Main function"""
    print("=== Product CSV Import Script ===")
    print()
    
    # Check if CSV file exists
    csv_file = 'products-master.csv'
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Create database connection
    print("🔗 Connecting to database...")
    conn = create_database_connection()
    print("✅ Database connected successfully")
    
    try:
        # Create products table
        print("\n🏗️ Creating products table...")
        if not create_products_table(conn):
            sys.exit(1)
        
        # Import CSV data
        print("\n📥 Importing CSV data...")
        processed, errors = import_csv_data(conn, csv_file)
        
        if processed > 0:
            # Show statistics
            get_table_stats(conn)
            print(f"\n🎉 Import completed successfully!")
        else:
            print(f"\n❌ Import failed - no data was imported")
            
    finally:
        conn.close()
        print("\n🔌 Database connection closed")

if __name__ == "__main__":
    main()
