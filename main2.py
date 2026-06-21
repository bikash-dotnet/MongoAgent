import streamlit as st
from pymongo import MongoClient
import urllib, io, json
import os
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="MongoDB Query Generator",
    page_icon="🗄️",
    layout="wide"
)

# Initialize session state variables
if 'query_generated' not in st.session_state:
    st.session_state.query_generated = False
if 'generated_query' not in st.session_state:
    st.session_state.generated_query = None
if 'raw_response' not in st.session_state:
    st.session_state.raw_response = None
if 'results' not in st.session_state:
    st.session_state.results = None
if 'executed' not in st.session_state:
    st.session_state.executed = False

# Initialize NVIDIA LLM
@st.cache_resource
def init_llm():
    try:
        llm = ChatNVIDIA(
            model="openai/gpt-oss-20b",
            temperature=0.0,
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
        return "Sample: Find top 5 expensive listings in New York"

# Initialize
llm = init_llm()
collection = init_mongodb()
sample = load_sample()

# Title and description
st.title("🗄️ MongoDB Query Generator with NVIDIA AI")
st.markdown("""
    Ask questions about Airbnb listings and get MongoDB aggregation queries.
    Preview the query before executing it on the database!
""")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    model_choice = st.selectbox(
        "Choose NVIDIA Model",
        [
            "openai/gpt-oss-20b",
            "meta/llama3-70b-instruct",
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
        step=0.1,
        help="Higher values make output more creative, lower values more deterministic"
    )
    
    st.divider()
    st.markdown("### 📊 Sample Queries")
    sample_queries = [
        "Find top 5 most expensive listings in New York",
        "Show me all superhosts with more than 100 reviews",
        "Find listings with WiFi and a pool in Los Angeles",
        "What is the average price for entire home/apt in Paris?",
        "Find hosts with the most listings",
        "Show me properties with 5 bedrooms and 3+ bathrooms"
    ]
    
    for sq in sample_queries:
        if st.button(f"📝 {sq[:30]}...", key=sq):
            st.session_state.question = sq
            st.rerun()

# Main area
col1, col2 = st.columns([3, 1])

with col1:
    # User input
    question = st.text_area(
        "💬 Enter your question:",
        value=st.session_state.get('question', ''),
        height=100,
        placeholder="Example: Show me top 5 most expensive listings in New York"
    )

with col2:
    st.markdown("### 🎯 Actions")
    generate_btn = st.button("🔄 Generate Query", use_container_width=True)
    
    # Clear button
    if st.button("🗑️ Clear All", use_container_width=True):
        st.session_state.query_generated = False
        st.session_state.generated_query = None
        st.session_state.raw_response = None
        st.session_state.results = None
        st.session_state.executed = False
        st.rerun()

# Prompt template (same as before)
prompt = """
        you are a very intelligent AI assistant who is expert in identifying relevant questions from user
        and converting into nosql mongodb aggregation pipeline query.
        Note: You have to just return the query as to use in aggregation pipeline nothing else. Don't return any other thing
        Please use the below schema to write the mongodb queries , dont use any other queries.
       schema:
       the mentioned mongodb collection talks about listing for an accommodation on Airbnb. The schema for this document represents the structure of the data, describing various properties related to the listing, host, reviews, location, and additional features. 
       your job is to get python code for the user question
       Here's a breakdown of its schema with descriptions for each field:

1. **_id**: Unique identifier for the listing.
2. **listing_url**: URL to the listing on Airbnb.
3. **name**: Name of the listing.
4. **summary**: A brief summary of the listing.
5. **space**: Description of the space provided.
6. **description**: Full description of the listing.
7. **neighborhood_overview**: Overview of the neighborhood.
8. **notes**: Additional notes provided by the host.
9. **transit**: Information about local transit options.
10. **access**: Information about what parts of the property guests can access.
11. **interaction**: Description of how the host will interact with the guests.
12. **house_rules**: House rules that guests must follow.
13. **property_type**: Type of property (e.g., House, Apartment).
14. **room_type**: Type of room (e.g., Entire home/apt, Private room).
15. **bed_type**: Type of bed provided.
16. **minimum_nights**: Minimum number of nights required for booking.
17. **maximum_nights**: Maximum number of nights allowed for booking.
18. **cancellation_policy**: Cancellation policy for the listing.
19. **last_scraped**: Date when the data was last scraped.
20. **calendar_last_scraped**: Date when the calendar was last scraped.
21. **first_review**: Date of the first review.
22. **last_review**: Date of the last review.
23. **accommodates**: Number of guests the listing accommodates.
24. **bedrooms**: Number of bedrooms.
25. **beds**: Number of beds.
26. **number_of_reviews**: Total number of reviews.
27. **bathrooms**: Number of bathrooms.
28. **amenities**: List of amenities provided.
29. **price**: Nightly price for the listing.
30. **security_deposit**: Amount of the security deposit.
31. **cleaning_fee**: Cleaning fee charged.
32. **extra_people**: Fee for extra guests.
33. **guests_included**: Number of guests included in the booking price.
34. **images**: Object containing URLs for various images of the listing.
35. **host**: Object containing information about the host.
36. **address**: Object containing detailed address of the listing.
37. **availability**: Object detailing availability for different time spans (30, 60, 90, and 365 days).
38. **review_scores**: Object containing different review scores (overall, accuracy, cleanliness, checkin, communication, location, value).
39. **reviews**: Array of review objects, each containing details about individual reviews.

##Embedded Objects

**Host Details:**
   - **host_id**: Unique identifier for the host.
   - **host_url**: URL to the host's profile.
   - **host_name**: Name of the host.
   - **host_since**: Date when the host joined Airbnb.
   - **host_location**: Location of the host.
   - **host_about**: Information about the host.
   - **host_response_time**: Average response time of the host.
   - **host_response_rate**: Host's response rate.
   - **host_acceptance_rate**: Rate at which the host accepts reservations.
   - **host_is_superhost**: Whether the host is a superhost.
   - **host_thumbnail_url**: URL to the host's thumbnail image.
   - **host_picture_url**: URL to the host's picture.
   - **host_neighbourhood**: Neighbourhood of the host.
   - **host_listings_count**: Number of listings the host has.
   - **host_total_listings_count**: Total number of listings including joint listings.
   - **host_verifications**: List of verifications the host has completed.
   - **host_has_profile_pic**: Whether the host has a profile picture.
   - **host_identity_verified**: Whether the host's identity has been verified.

**Address Details:**
   - **street**: Street address of the listing.
   - **suburb**: Suburb in which the listing is located.
   - **government_area**: Government area the listing belongs to.
   - **market**: Market area for the listing.
   - **country**: Country where the listing is located.
   - **country_code**: Country code for the listing.
   - **location**: Object containing geographical coordinates (longitude, latitude).

**Location Object:**
   - **type**: Type of location data (Point).
   - **coordinates**: Array of coordinate values (longitude, latitude).
   - **is_location_exact**: Whether the location is exact.

**Images Object:**
   - **thumbnail_url**: URL of the thumbnail image.
   - **medium_url**: URL of the medium-sized image.
   - **picture_url**: URL of the picture.
   - **xl_picture_url**: URL of the extra-large picture.

##Arrays

**Amenities**:
   - List of amenities available at the listing (e.g., Wifi, Kitchen, etc.).

**Reviews**:
   - **_id**: Unique identifier for the review.
   - **date**: Date of the review.
   - **listing_id**: ID of the listing reviewed.
   - **reviewer_id**: ID of the reviewer.
   - **reviewer_name**: Name of the reviewer.
   - **comments**: Text of the comment left by the reviewer.

This schema provides a comprehensive view of the data structure for an Airbnb listing in MongoDB, 
including nested and embedded data structures that add depth and detail to the document.
use the below sample_examples to generate your queries perfectly
sample_example:

Below are several sample user questions related to the MongoDB document provided, 
and the corresponding MongoDB aggregation pipeline queries that can be used to fetch the desired data.
Use them wisely.

sample_question: {sample}
As an expert you must use them whenever required.
Note: You have to just return the query nothing else. Don't return any additional text with the query.Please follow this strictly
input:{question}
output:
"""

# Generate query
if generate_btn and question:
    if llm:
        try:
            with st.spinner("🧠 Generating query with NVIDIA AI..."):
                # Update model if changed
                if model_choice != llm.model:
                    llm = ChatNVIDIA(
                        model=model_choice,
                        temperature=temperature,
                        nvidia_api_key=os.getenv("NVIDIA_API_KEY")
                    )
                
                # Create chain
                query_with_prompt = PromptTemplate(
                    template=prompt,
                    input_variables=["question", "sample"]
                )
                llmchain = query_with_prompt | llm | StrOutputParser()
                
                # Get response
                response = llmchain.invoke({
                    "question": question,
                    "sample": sample
                })
                
                # Parse query
                query = response.strip()
                
                # Store in session state
                st.session_state.generated_query = query
                st.session_state.raw_response = response
                st.session_state.query_generated = True
                st.session_state.executed = False
                st.session_state.results = None
                
                st.success("✅ Query generated successfully!")
                st.rerun()
                
        except json.JSONDecodeError as e:
            st.error(f"❌ Failed to parse query: {str(e)}")
            st.code(response, language="json")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    
elif generate_btn and not question:
    st.warning("⚠️ Please enter a question first!")

# Display generated query if available
if st.session_state.query_generated and st.session_state.generated_query:
    st.divider()
    st.subheader("📝 Generated MongoDB Query")
    
    # Query preview with formatting
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Display query in a nice format
        st.json(st.session_state.generated_query)
        
        # Also show raw JSON
        with st.expander("🔧 View Raw JSON"):
            st.code(
                json.dumps(st.session_state.generated_query, indent=2),
                language="json"
            )
    
    with col2:
        # Execute button
        execute_btn = st.button(
            "🚀 Execute Query",
            use_container_width=True,
            type="primary"
        )
        
        # Edit query button
        if st.button("✏️ Edit Query", use_container_width=True):
            st.session_state.edit_mode = True
    
    # Edit mode
    if st.session_state.get('edit_mode', False):
        st.subheader("✏️ Edit Query")
        edited_query = st.text_area(
            "Edit the query JSON:",
            value=json.dumps(st.session_state.generated_query, indent=2),
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
    
    # Execute query
    if execute_btn:
        if collection:
            try:
                with st.spinner("🔄 Executing query on MongoDB..."):
                    pipeline = json.loads(st.session_state.generated_query)
                    results = list(collection.aggregate(pipeline))
                    st.session_state.results = results
                    st.session_state.executed = True
                    
                    if results:
                        st.success(f"✅ Found {len(results)} results!")
                    else:
                        st.info("ℹ️ No results found for this query")
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Database error: {str(e)}")

# Display results if executed
if st.session_state.executed and st.session_state.results is not None:
    st.divider()
    st.subheader(f"📊 Results ({len(st.session_state.results)})")
    
    results = st.session_state.results
    
    if results:
        # Display count and options
        col1, col2 = st.columns([2, 1])
        with col1:
            st.caption(f"Showing {len(results)} result(s)")
        
        with col2:
            # Export options
            export_format = st.selectbox(
                "Export as",
                ["JSON", "CSV"],
                key="export_format"
            )
            
            if st.button("📥 Download Results"):
                if export_format == "JSON":
                    json_str = json.dumps(results, indent=2, default=str)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name="query_results.json",
                        mime="application/json"
                    )
                else:
                    # Simple CSV conversion (you can enhance this)
                    import pandas as pd
                    df = pd.DataFrame(results)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )
        
        # Display results in a nice format
        view_option = st.radio(
            "View as:",
            ["Cards", "Table", "JSON"],
            horizontal=True
        )
        
        if view_option == "Cards":
            # Card view
            cols_per_row = 2
            for i in range(0, len(results), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(results):
                        doc = results[i + j]
                        with col:
                            st.card(
                                json.dumps(doc, indent=2, default=str)[:500] + "...",
                                title=doc.get('name', f"Listing {i+j+1}")
                            )
        
        elif view_option == "Table":
            # Table view - show key fields
            import pandas as pd
            # Flatten nested fields for display
            flattened = []
            for doc in results[:50]:  # Limit for display
                flat_doc = {
                    'name': doc.get('name', ''),
                    'price': doc.get('price', ''),
                    'room_type': doc.get('room_type', ''),
                    'property_type': doc.get('property_type', ''),
                    'bedrooms': doc.get('bedrooms', ''),
                    'bathrooms': doc.get('bathrooms', ''),
                    'number_of_reviews': doc.get('number_of_reviews', 0),
                }
                # Add nested fields if they exist
                if 'address' in doc:
                    flat_doc['market'] = doc['address'].get('market', '')
                    flat_doc['country'] = doc['address'].get('country', '')
                if 'host' in doc:
                    flat_doc['host_name'] = doc['host'].get('host_name', '')
                    flat_doc['is_superhost'] = doc['host'].get('host_is_superhost', False)
                flattened.append(flat_doc)
            
            df = pd.DataFrame(flattened)
            st.dataframe(df, use_container_width=True)
        
        else:
            # JSON view
            st.json(results)

# Footer
st.divider()
st.caption("🚀 Powered by NVIDIA AI | MongoDB Aggregation Query Generator")