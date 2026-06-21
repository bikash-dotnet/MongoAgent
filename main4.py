import streamlit as st
from pymongo import MongoClient
import urllib, io, json, os
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pandas as pd
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="MongoDB Query Generator",
    page_icon="🗄️",
    layout="wide"
)

# Initialize ALL session state variables
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'query_generated': False,
        'generated_query': None,
        'raw_response': None,
        'results': None,
        'executed': False,
        'query_type': "aggregation",
        'query_history': [],
        'schema_text': "",
        'prompt_template': "",
        'question': "",
        'execute_clicked': False,  # New flag for tracking execute button
        'edit_mode': False,
        'execution_time': 0,
        'error_message': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize all session state
init_session_state()

# Callbacks for programmatic updates
def set_question(q):
    st.session_state.question = q

def clear_all():
    st.session_state.question = ""
    st.session_state.query_generated = False
    st.session_state.generated_query = None
    st.session_state.results = None
    st.session_state.executed = False
    st.session_state.execute_clicked = False
    st.session_state.error_message = None

def execute_find_query(collection, query):
    filter_dict = {}
    projection = None
    sort = None
    limit = 0
    skip = 0
    
    if isinstance(query, dict):
        # 1. Extract filter
        if "filter" in query and isinstance(query["filter"], dict):
            filter_dict = query["filter"]
        elif "find" in query and isinstance(query["find"], dict):
            filter_dict = query["find"]
        elif "find" in query and isinstance(query["find"], str):
            filter_dict = query.get("filter", {})
            if not isinstance(filter_dict, dict):
                filter_dict = {}
        else:
            filter_dict = {k: v for k, v in query.items() if k not in ["find", "limit", "sort", "projection", "skip"]}
        
        # 2. Extract projection
        projection = query.get("projection") or query.get("project")
        if projection and not isinstance(projection, dict):
            projection = None
            
        # 3. Extract limit
        try:
            limit = int(query.get("limit", 0))
        except (ValueError, TypeError):
            limit = 0
            
        # 4. Extract skip
        try:
            skip = int(query.get("skip", 0))
        except (ValueError, TypeError):
            skip = 0
            
        # 5. Extract sort
        sort_val = query.get("sort")
        if isinstance(sort_val, dict):
            sort = list(sort_val.items())
        elif isinstance(sort_val, list):
            sort = []
            for item in sort_val:
                if isinstance(item, list) and len(item) == 2:
                    sort.append(tuple(item))
                elif isinstance(item, dict):
                    sort.extend(item.items())
        if not sort:
            sort = None
    else:
        filter_dict = query
    
    cursor = collection.find(filter_dict, projection=projection, skip=skip, limit=limit)
    if sort:
        cursor = cursor.sort(sort)
    return list(cursor)

# Initialize NVIDIA LLM
@st.cache_resource
def init_llm(model_name, temperature):
    try:
        llm = ChatNVIDIA(
            model=model_name,
            temperature=temperature,
            nvidia_api_key=os.getenv("NVIDIA_API_KEY")
        )
        return llm
    except Exception as e:
        st.error(f"❌ Failed to initialize NVIDIA LLM: {str(e)}")
        return None

# Initialize MongoDB connection
@st.cache_resource
def init_mongodb():
    try:
        client = MongoClient(os.getenv("MONGODB_URI"))
        # Test connection
        client.admin.command('ping')
        db = client["sample_airbnb"]
        collection = db["listingsAndReviews"]
        return collection
    except Exception as e:
        st.error(f"❌ Failed to connect to MongoDB: {str(e)}")
        return None

# Load sample examples
@st.cache_data
def load_sample():
    try:
        with io.open("sample.txt", "r", encoding="utf-8") as f1:
            return f1.read()
    except FileNotFoundError:
        st.warning("⚠️ sample.txt not found. Using default samples.")
        return """
        Sample 1:
        Question: "Find top 5 expensive listings in New York"
        Query: [{"$match": {"address.market": "New York"}}, {"$sort": {"price": -1}}, {"$limit": 5}]
        """

# Initialize
collection = init_mongodb()
sample = load_sample()

# Title
st.title("🗄️ MongoDB Query Generator with NVIDIA AI")
st.markdown("Generate MongoDB queries from natural language with AI assistance!")

# Debug info (remove in production)
with st.expander("🔍 Debug Info", expanded=False):
    st.write("Session State Keys:", list(st.session_state.keys()))
    st.write("Collection connected:", collection is not None)
    if collection is not None:
        try:
            count = collection.count_documents({})
            st.write(f"Documents in collection: {count}")
        except:
            st.write("❌ Could not count documents")

# Tab layout
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Query Generator", 
    "📊 Results", 
    "📝 Prompt Management",
    "🗃️ Schema Management", 
    "📜 History"
])

# ==================== TAB 1: Query Generator ====================
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # User input with session state
        question = st.text_area(
            "💬 Enter your question:",
            height=100,
            placeholder="Example: Show me top 5 most expensive listings in New York",
            key="question"
        )
    
    with col2:
        st.markdown("### ⚙️ Query Settings")
        
        # Query type selection
        query_type = st.radio(
            "Query Type:",
            ["Auto", "Aggregation Pipeline", "Find Query"],
            help="Auto: AI decides best approach. Aggregation: For complex queries. Find: For simple filtering"
        )
        
        # Model selection
        model_choice = st.selectbox(
            "NVIDIA Model",
            [
                "openai/gpt-oss-20b",
                "meta/llama3-8b-instruct",
                "mistralai/mistral-7b-instruct",
                "mistralai/mixtral-8x7b-instruct"
            ]
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1
        )
        
        # Action buttons with proper handling
        generate_btn = st.button("🔄 Generate Query", use_container_width=True, type="primary")
        
        st.button("🗑️ Clear All", use_container_width=True, on_click=clear_all)
    
    # Sample queries
    with st.expander("📝 Sample Queries"):
        sample_queries = [
            ("Top 5 expensive in NYC", "Find top 5 most expensive listings in New York"),
            ("Superhosts with 100+ reviews", "Show me all superhosts with more than 100 reviews"),
            ("WiFi and Pool in LA", "Find listings with WiFi and a pool in Los Angeles"),
            ("Average price in Paris", "What is the average price for entire home/apt in Paris?"),
            ("Hosts with most listings", "Find hosts with the most listings"),
            ("5 bedrooms, 3+ bathrooms", "Show me properties with 5 bedrooms and 3+ bathrooms")
        ]
        
        cols = st.columns(3)
        for idx, (label, query) in enumerate(sample_queries):
            with cols[idx % 3]:
                st.button(f"📌 {label}", key=f"sample_{idx}", on_click=set_question, args=(query,))
    
    # ============ GENERATE QUERY ============
    if generate_btn and question:
        st.session_state.execute_clicked = False  # Reset execute flag
        llm = init_llm(model_choice, temperature)
        
        if llm and collection is not None:
            try:
                with st.spinner("🧠 Generating query with NVIDIA AI..."):
                    # Build prompt
                    prompt = f"""
                    Convert the following question to a MongoDB query.
                    
                    Database Schema:
                    {sample}
                    
                    Question: {question}
                    
                    Important: 
                    - Return ONLY the MongoDB query
                    - For aggregation pipeline, return JSON array: [{{"$match": ...}}]
                    - For find query, return JSON object: {{"find": ...}}
                    - No explanations, no markdown, just the query
                    
                    Query:
                    """
                    
                    # Get response
                    response = llm.invoke(prompt)
                    response_text = response.content.strip()
                    
                    # Log response for debugging
                    st.session_state.raw_response = response_text
                    
                    # Parse JSON
                    try:
                        # Remove markdown if present
                        if "```json" in response_text:
                            response_text = response_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in response_text:
                            response_text = response_text.split("```")[1].split("```")[0].strip()
                        
                        query = json.loads(response_text)
                        
                        # Determine query type
                        if isinstance(query, dict) and "find" in query:
                            query_type_detected = "find"
                        elif isinstance(query, list):
                            query_type_detected = "aggregation"
                        else:
                            query_type_detected = "unknown"
                        
                        # Store in session state
                        st.session_state.generated_query = query
                        st.session_state.query_generated = True
                        st.session_state.executed = False
                        st.session_state.results = None
                        st.session_state.query_type = query_type_detected
                        st.session_state.error_message = None
                        
                        st.success(f"✅ Query generated successfully! (Type: {query_type_detected})")
                        st.rerun()
                        
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Failed to parse query: {str(e)}")
                        st.code(response_text, language="json")
                        st.session_state.error_message = "Failed to parse AI response"
                        
            except Exception as e:
                st.error(f"❌ Error generating query: {str(e)}")
                st.session_state.error_message = str(e)
        else:
            if collection is None:
                st.error("❌ MongoDB connection failed. Please check credentials.")
    
    # ============ DISPLAY GENERATED QUERY ============
    if st.session_state.query_generated and st.session_state.generated_query:
        st.divider()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            query_type_label = {
                "aggregation": "🔄 Aggregation Pipeline",
                "find": "🔍 Find Query",
                "unknown": "❓ Unknown Type"
            }
            st.subheader(f"📝 Generated {query_type_label.get(st.session_state.query_type, 'Query')}")
        
        with col2:
            # Execute button with proper handler
            execute_btn = st.button(
                "🚀 Execute Query", 
                use_container_width=True, 
                type="primary",
                key="execute_button"
            )
        
        with col3:
            if st.button("✏️ Edit Query", use_container_width=True):
                st.session_state.edit_mode = not st.session_state.edit_mode
                st.rerun()
        
        # Display query
        st.code(
            json.dumps(st.session_state.generated_query, indent=2),
            language="json"
        )
        
        # Edit mode
        if st.session_state.edit_mode:
            st.subheader("✏️ Edit Query")
            
            if st.session_state.query_type == "find":
                edit_prompt = json.dumps(st.session_state.generated_query, indent=2)
            else:
                edit_prompt = json.dumps(st.session_state.generated_query, indent=2)
            
            edited_query = st.text_area(
                "Edit the query JSON:",
                value=edit_prompt,
                height=200
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Apply Changes"):
                    try:
                        st.session_state.generated_query = json.loads(edited_query)
                        st.session_state.edit_mode = False
                        st.success("✅ Query updated!")
                        st.rerun()
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON: {str(e)}")
            
            with col2:
                if st.button("❌ Cancel Edit"):
                    st.session_state.edit_mode = False
                    st.rerun()
        
        # ============ EXECUTE QUERY ============
        if execute_btn:  # This will execute when button is clicked
            st.session_state.execute_clicked = True  # Set flag
            
            if collection is None:
                st.error("❌ MongoDB connection is not available")
                st.session_state.execute_clicked = False
            else:
                try:
                    with st.spinner("🔄 Executing query on MongoDB..."):
                        start_time = time.time()
                        
                        # Execute based on query type
                        query = st.session_state.generated_query
                        print("Query: ", query)
                        print("Query Type: ", st.session_state.query_type)
                        if st.session_state.query_type == "find":
                            results = execute_find_query(collection, query)
                        elif st.session_state.query_type == "aggregation":
                            results = list(collection.aggregate(query))
                        else:
                            # Try both
                            try:
                                results = list(collection.aggregate(query))
                                st.session_state.query_type = "aggregation"
                            except:
                                try:
                                    results = execute_find_query(collection, query)
                                    st.session_state.query_type = "find"
                                except:
                                    raise Exception("Could not execute query. Please check the format.")
                        
                        execution_time = time.time() - start_time
                        
                        # Store results
                        st.session_state.results = results
                        st.session_state.executed = True
                        st.session_state.execution_time = execution_time
                        st.session_state.execute_clicked = False  # Reset flag
                        
                        # Save to history
                        st.session_state.query_history.append({
                            'timestamp': datetime.now().isoformat(),
                            'question': st.session_state.question,
                            'query_type': st.session_state.query_type,
                            'query': st.session_state.generated_query,
                            'result_count': len(results),
                            'execution_time': execution_time
                        })
                        
                        if results:
                            st.success(f"✅ Found {len(results)} results in {execution_time:.3f} seconds!")
                        else:
                            st.info("ℹ️ No results found for this query")
                        
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Database error: {str(e)}")
                    st.session_state.error_message = str(e)
                    st.session_state.execute_clicked = False

# ==================== TAB 2: Results ====================
with tab2:
    if st.session_state.executed and st.session_state.results is not None:
        results = st.session_state.results
        
        if results:
            st.subheader(f"📊 Results ({len(results)})")
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Results", len(results))
            with col2:
                st.metric("Execution Time", f"{st.session_state.execution_time:.3f}s")
            with col3:
                query_type_emoji = "🔍" if st.session_state.query_type == "find" else "🔄"
                st.metric("Query Type", f"{query_type_emoji} {st.session_state.query_type.title()}")
            
            # View options
            view_option = st.radio(
                "View as:",
                ["Cards", "Table", "JSON"],
                horizontal=True
            )
            
            if view_option == "Cards":
                cols_per_row = 2
                for i in range(0, min(len(results), 20), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(results):
                            doc = results[i + j]
                            with col:
                                with st.container(border=True):
                                    st.markdown(f"### {doc.get('name', f'Listing {i+j+1}')}")
                                    if 'price' in doc:
                                        st.markdown(f"**Price:** ${doc['price']}")
                                    if 'room_type' in doc:
                                        st.markdown(f"**Room Type:** {doc['room_type']}")
                                    if 'property_type' in doc:
                                        st.markdown(f"**Property Type:** {doc['property_type']}")
                                    with st.expander("View Full Details"):
                                        st.json(doc)
            
            elif view_option == "Table":
                flattened = []
                for doc in results[:100]:
                    flat_doc = {}
                    if 'name' in doc:
                        flat_doc['Name'] = doc['name']
                    if 'price' in doc:
                        flat_doc['Price'] = doc['price']
                    if 'room_type' in doc:
                        flat_doc['Room Type'] = doc['room_type']
                    if 'property_type' in doc:
                        flat_doc['Property Type'] = doc['property_type']
                    if 'bedrooms' in doc:
                        flat_doc['Bedrooms'] = doc['bedrooms']
                    if 'bathrooms' in doc:
                        flat_doc['Bathrooms'] = doc['bathrooms']
                    if 'number_of_reviews' in doc:
                        flat_doc['Reviews'] = doc['number_of_reviews']
                    if 'address' in doc:
                        flat_doc['Market'] = doc['address'].get('market', '')
                    if 'host' in doc:
                        flat_doc['Superhost'] = doc['host'].get('host_is_superhost', False)
                    flattened.append(flat_doc)
                
                if flattened:
                    df = pd.DataFrame(flattened)
                    st.dataframe(df, use_container_width=True, height=400)
            
            else:
                st.json(results)
        else:
            st.info("No results to display")
    else:
        st.info("No query executed yet. Generate and execute a query first!")

# ==================== TAB 3-5: Keep from previous version ====================
with tab3:
    st.info("Prompt management tab (simplified for brevity)")

with tab4:
    st.info("Schema management tab (simplified for brevity)")

with tab5:
    if st.session_state.query_history:
        history_df = pd.DataFrame(st.session_state.query_history)
        st.dataframe(history_df[['timestamp', 'question', 'query_type', 'result_count', 'execution_time']])
    else:
        st.info("No query history yet")

# Footer
st.divider()
st.caption("🚀 Powered by NVIDIA AI | MongoDB Query Generator v2.0")

# Debug section at bottom
if st.session_state.get('debug', False):
    with st.expander("🔍 Debug Information"):
        st.write("Session State:")
        for key in st.session_state:
            if key not in ['generated_query', 'results', 'query_history']:
                st.write(f"{key}: {st.session_state[key]}")