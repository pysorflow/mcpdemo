# 🛍️ MCP Product Management System

A comprehensive **Model Context Protocol (MCP)** server for product inventory management with PostgreSQL database backend, Docker containerization, and multiple AI platform integrations.

## 🎯 **System Overview**

This system provides a sophisticated product management platform with:
- **9,739 products** across multiple categories
- **9 advanced MCP tools** with Django-style filtering
- **PostgreSQL database** with Docker containerization
- **Multi-platform AI integration** (Claude Desktop, Ollama, Perplexity)
- **Advanced filtering & pagination** capabilities
- **Natural language query processing**

---

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude Desktop│    │   MCP Inspector  │    │     Ollama      │    │   Perplexity    │
│                 │    │                  │    │     Bridge      │    │     Local       │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                       │                      │
          └──────────────────────┼───────────────────────┼──────────────────────┘
                                 │                       │
                    ┌────────────┴───────────┐           │
                    │   Local MCP Server     │           │
                    │ (local_mcp_server.py)  │           │
                    │   • 9 Advanced Tools   │           │
                    │   • Django Filtering   │           │
                    │   • Pagination         │           │
                    └────────────┬───────────┘           │
                                 │                       │
                    ┌────────────┴───────────┐           │
                    │   Docker MCP Server    │           │
                    │   (mcp_server.py)      │           │
                    │   • Container-based    │           │
                    └────────────┬───────────┘           │
                                 │                       │
                    ┌────────────┴───────────┐           │
                    │   PostgreSQL DB        │◄─────────-┘
                    │   • 9,739 products     │   Direct Connection
                    │   • Full-text search   │   (ollama_mcp_bridge.py)
                    │   • Advanced indexes   │
                    └────────────────────────┘
```

---

## 🛠️ **Setup & Installation**

### **Prerequisites**
- Docker & Docker Compose
- **Python 3.10+** (required for MCP library)
- Node.js (for MCP Inspector)
- Ollama (optional, for Ollama integration)

### **🔍 Python Version Check**
```bash
# Check your Python version first
python3 --version

# If you have Python < 3.10, you need to upgrade or use a different Python version
# On macOS with Homebrew:
# brew install python@3.11

# On Ubuntu/Debian:
# sudo apt update && sudo apt install python3.11

# On Windows: Download from python.org
```

### **1. Clone & Setup**
```bash
git clone https://github.com/pysorflow/mcpdemo.git
cd mcpdemo

# Create Python virtual environment (use Python 3.10+)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# If python3 is too old, try specific version:
# python3.11 -m venv venv
# python3.10 -m venv venv

# Install dependencies
pip install -r requirements.txt
```

### **2. Start Docker Services**
```bash
# Start PostgreSQL database
docker-compose up -d

# Verify services are running
docker-compose ps
```

### **3. Import Product Data**
```bash
# Import 9,739 products into database
python import_products.py
```

### **4. Test System**
```bash
# Run comprehensive tests
python test.py
```

---

## 🔧 **Available MCP Tools**

### **Core Tools**
1. **`get_product`** - Get detailed product information by SKU
2. **`list_products`** - List products with optional category filtering
3. **`search_products`** - Basic search across product fields
4. **`advanced_search_products`** - Comprehensive search with filtering
5. **`update_stock`** - Update product stock levels

### **Advanced Tools**
6. **`filter_products`** - **Django-style filtering** with pagination
   - Field lookups: `category__icontains`, `stock__gte`, `price__lte`, etc.
   - Sorting: `["-stock", "title"]`
   - Pagination: `page`, `page_size`

7. **`get_categories`** - List all product categories and subcategories
8. **`get_low_stock_products`** - Find products with low inventory
9. **`get_filter_stats`** - Get filtering statistics and breakdowns

### **Django-Style Filter Examples**
```json
{
  "filters": {
    "category__icontains": "shirt",
    "color__icontains": "blue", 
    "stock__gte": 50,
    "price__lte": 25.00,
    "size__in": ["L", "XL"]
  },
  "ordering": ["-stock", "price"],
  "page": 1,
  "page_size": 20
}
```

---

## 🖥️ **Platform Integration**

## **1. MCP Inspector (Testing & Development)**

### **Setup & Run**
```bash
# Install MCP Inspector globally
npm install -g @modelcontextprotocol/inspector

# Start local MCP server + Inspector
npx @modelcontextprotocol/inspector python local_mcp_server.py
```

### **Usage**
- **URL**: Opens automatically in browser (usually `http://localhost:5173`)
- **Features**: Test all 9 tools, view JSON schemas, debug responses
- **Best for**: Development, testing, debugging MCP tools

---

## **2. Claude Desktop Integration**

### **Setup Configuration**
1. **Locate Claude Desktop config file:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add MCP server configuration:**
```json
{
  "mcpServers": {
    "product-manager": {
      "command": "/Users/arunss/Documents/myroot/mcpdemo/run_mcp_server.sh",
      "args": []
    }
  }
}
```

3. **Make shell script executable:**
```bash
chmod +x run_mcp_server.sh
```

### **Usage**
- **Restart Claude Desktop** after config changes
- **Natural language queries**: "Show me blue shirts under $20 with good stock"
- **Complex filtering**: "Find size XL products sorted by price"
- **Business queries**: "What are our top categories by inventory?"

### **Example Queries**
- *"Give me details of SKU 120715"*
- *"Show products with more than 1000 units in stock"*
- *"What black items do we have from Gildan warehouse?"*
- *"Filter polo shirts with prices between $15 and $30"*

---

## **3. Ollama Integration**

### **Setup Ollama**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download recommended models
ollama pull qwen2.5:7b-instruct  # Best for natural language
ollama pull llama3.2:1b          # Fastest, lightweight
ollama pull llama3.1:8b          # Balanced performance
```

### **Run Ollama Bridge**
```bash
# Start enhanced Ollama bridge
python ollama_mcp_bridge.py
```

### **Features**
- **Model selection** at startup
- **Natural language processing** with LLM-based query parsing
- **Advanced filtering** through conversational interface
- **Statistics commands**: `stats`, `examples`, `models`

### **Usage Example**
```
💬 Your question [qwen2.5:7b-instruct]: Show me blue shirts under $20 with good stock

🔍 Analyzing: 'Show me blue shirts under $20 with good stock'
🎯 Initial classification: ADVANCED_FILTER
🤖 LLM filter analysis: {"filters": {"color__icontains": "blue", "category__icontains": "shirt", "price__lte": 20, "stock__gte": 50}, "ordering": ["-stock"], "page_size": 10}
📊 Data retrieved: 1247 characters

🤖 Answer:
Based on your search for blue shirts under $20 with good stock, I found several excellent options...
```

---

## **4. Perplexity Local Integration**

### **Setup**
1. **Install Perplexity Desktop** or use **Perplexity API**
2. **Configure MCP connection** in Perplexity settings
3. **Add server endpoint:**

```json
{
  "mcp_servers": {
    "product_manager": {
      "type": "local",
      "command": "python",
      "args": ["/Users/arunss/Documents/myroot/mcpdemo/local_mcp_server.py"],
      "working_directory": "/Users/arunss/Documents/myroot/mcpdemo"
    }
  }
}
```

### **Usage**
- **Research queries**: "Analyze our product inventory distribution"
- **Business intelligence**: "What's our stock situation across categories?"
- **Data exploration**: "Show me patterns in our product pricing"

---

## 📋 **Usage Workflows**

### **Development Workflow**
1. **Start Docker**: `docker-compose up -d`
2. **Test with Inspector**: `npx @modelcontextprotocol/inspector python local_mcp_server.py`
3. **Debug tools**, test filters, verify responses
4. **Deploy to AI platforms**

### **Production Workflow**
1. **Docker services running**: `docker-compose up -d`
2. **Claude Desktop configured** with shell script
3. **Ollama bridge available** for advanced NLP
4. **Multiple access points** for different use cases

### **Business User Workflow**
1. **Open Claude Desktop**
2. **Ask natural language questions**:
   - *"What's our inventory status?"*
   - *"Show me slow-moving products"*
   - *"Find products that need restocking"*
3. **Get instant, detailed responses**

---

## 🔍 **Sample Questions & Use Cases**

### **Basic Queries**
- *"Give me details of product SKU 120715"*
- *"List all T-shirt categories we have"*
- *"Show me products with low stock"*

### **Advanced Filtering**
- *"Show blue shirts under $20 with good stock levels"*
- *"Find size XL products sorted by price ascending"*
- *"What black items do we have from Gildan warehouse?"*

### **Business Intelligence**
- *"What are our top 5 categories by product count?"*
- *"Show me inventory distribution across warehouses"*
- *"Which products have the highest stock levels?"*

### **Inventory Management**
- *"Products with more than 1000 units in stock"*
- *"Show items that are running low on inventory"*
- *"What's our most expensive product in each category?"*

### **Complex Analysis**
- *"Filter polo shirts with prices between $15 and $30"*
- *"Show me all products from Hanes with sizes L and XL"*
- *"Find products with zero stock sorted by category"*

---

## 🧪 **Testing**

### **Run Test Suite**
```bash
python test.py
```

### **Test Individual Components**
```bash
# Test database connection
python -c "import psycopg2; print('DB OK')"

# Test MCP server
python local_mcp_server.py

# Test Ollama bridge
python ollama_mcp_bridge.py
```

### **Verification Checklist**
- ✅ Docker services running (`docker-compose ps`)
- ✅ Database populated (9,739 products)
- ✅ MCP tools functional (test.py passes)
- ✅ Claude Desktop integration working
- ✅ Ollama models available

---

## 📁 **File Structure**

```
mcpdemo/
├── 📄 README.md                 # This comprehensive guide
├── 🐳 docker-compose.yml        # Docker services configuration
├── 🐳 Dockerfile               # MCP server container
├── 📋 requirements.txt         # Python dependencies
├── 🛠️ local_mcp_server.py      # Main MCP server (9 tools)
├── 🛠️ mcp_server.py            # Docker-based MCP server
├── 🤖 ollama_mcp_bridge.py     # Enhanced Ollama integration
├── 📊 import_products.py       # Data import script
├── 🧪 test.py                  # Comprehensive test suite
├── 📝 sample_questions.txt     # 25 sample questions + examples
├── ⚙️ run_mcp_server.sh        # Claude Desktop shell script
├── ⚙️ claude_desktop_config.json # Claude Desktop configuration
├── 📦 products-master.csv      # Product data (9,739 items)
└── 📁 venv/                    # Python virtual environment
```

---

## ⚠️ **Troubleshooting**

### **Common Issues**

**1. Database Connection Failed**
```bash
# Check Docker services
docker-compose ps

# Restart if needed
docker-compose down && docker-compose up -d
```

**2. Python Version Error (MCP requires Python 3.10+)**
```bash
# Check your Python version
python3 --version

# If version is < 3.10, upgrade Python:
# macOS (Homebrew): brew install python@3.11
# Ubuntu/Debian: sudo apt install python3.11
# Windows: Download from python.org

# Create virtual environment with correct Python version
python3.11 -m venv venv  # or python3.10
source venv/bin/activate
pip install -r requirements.txt
```

**3. MCP Server Not Starting**
```bash
# Check Python environment
source venv/bin/activate
pip install -r requirements.txt
```

**4. Claude Desktop Not Connecting**
- Verify config file path
- Check shell script permissions: `chmod +x run_mcp_server.sh`
- Restart Claude Desktop after config changes

**5. Ollama Models Not Found**
```bash
# List available models
ollama list

# Download missing models
ollama pull qwen2.5:7b-instruct
```

---

## 🚀 **Advanced Features**

### **Django-Style Filtering**
- **Field lookups**: `__icontains`, `__exact`, `__gte`, `__lte`, `__in`
- **Pagination**: Automatic with page/page_size
- **Sorting**: Multi-field with direction control
- **Global search**: Across all text fields

### **Natural Language Processing**
- **LLM-powered query parsing** in Ollama bridge
- **Intent classification** for optimal tool selection
- **Fallback strategies** for complex queries
- **Context-aware responses**

### **Performance Optimizations**
- **Database indexes** on key fields
- **Connection pooling** for high-load scenarios
- **Query optimization** for large datasets
- **Efficient pagination** with offset/limit

---

## 📈 **Statistics**

- **Total Products**: 9,739
- **Categories**: 15+ major categories
- **MCP Tools**: 9 advanced tools
- **Database**: PostgreSQL 16
- **Docker Services**: 2 containers
- **AI Platforms**: 4 integrations
- **Filter Options**: 16 Django-style filters
- **Status**: ✅ **FULLY OPERATIONAL**

---

## 🎯 **Next Steps**

1. **Explore Sample Questions**: Check `sample_questions.txt` for 25 comprehensive examples
2. **Customize Tools**: Modify MCP tools for your specific needs
3. **Scale Database**: Add more products or customize schema
4. **Extend AI Integration**: Add more AI platforms or models
5. **Build Applications**: Use MCP protocol for custom applications

---

**🎉 Your MCP Product Management System is ready for production use!**

*Last updated: August 2025*
*System tested and verified across all platforms*
