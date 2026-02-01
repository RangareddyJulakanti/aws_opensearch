import streamlit as st
import time
import pandas as pd
from utils import get_opensearch_client, load_config
import os

# Load config to ensure env vars are available
load_config()

# Page Config
st.set_page_config(
    page_title="OpenSearch Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Premium Design ---
st.markdown("""
<style>
    /* Main Background & Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(to bottom right, #f8f9fa, #e9ecef);
    }

    /* Titles & Headers */
    h1, h2, h3 {
        color: #1a1a1a;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Cards/Containers */
    .css-1r6slb0, .stMarkdown, .stDataFrame {
        border-radius: 12px;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
        border: none;
        padding: 0.6rem 1.2rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Primary Button Style */
    button[kind="primary"] {
        background: linear-gradient(90deg, #4f46e5 0%, #3b82f6 100%);
        color: white;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #f0f0f0;
    }

    /* Success/Error Messages */
    .stSuccess, .stError, .stInfo {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4f46e5;
        box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
    }

</style>
""", unsafe_allow_html=True)

# --- Header ---
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://opensearch.org/assets/brand/SVG/Logo/opensearch_logo_default.svg", width=60)
with col2:
    st.title("OpenSearch Manager")
    st.markdown("*A premium interface for your Serverless Collection*")

st.divider()

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Connection Status Indicator
    client = get_opensearch_client()
    if client:
        try:
            # Try basic info first (works for Provisioned)
            # For Serverless (AOSS), root '/' might 404, so we fallback to listing indices logic or just 'ping'
            try:
                info = client.info()
                st.success("🟢 Connected to OpenSearch (Provisioned)")
                with st.expander("Cluster Info"):
                    st.json(info)
            except Exception:
                # Fallback for AOSS which may not return info() cleanly or returns 404 on root
                # Try listing indices as a "ping"
                client.cat.indices(format="json") 
                st.success("🟢 Connected to OpenSearch (Serverless)")
        except Exception as e:
            st.error("🔴 Connection Failed")
            st.error(f"Error: {str(e)}")
            st.warning("Tip: Check your Data Access Policy in AWS console if you see 403 or 404.")
    else:
        st.warning("🟠 Configuration Missing")

    st.markdown("---")
    
    # Manual Override
    st.subheader("Connection Settings")
    env_url = os.getenv('OPENSEARCH_URL', '')
    url_input = st.text_input("Endpoint URL", value=env_url, type="password", help="Enter your OpenSearch Serverless Endpoint")
    region_input = st.text_input("AWS Region", value=os.getenv('AWS_REGION', 'us-east-1'))

    if url_input != env_url:
        st.info("💡 Update your `.env` file for persistence.")

# --- Main Interface ---

tabs = st.tabs(["Dashboard", "Data Entry", "Search Explorer", "Settings"])

# --- Tab 1: Dashboard (Stats & Index Management) ---
with tabs[0]:
    st.subheader("📊 Cluster Overview")
    
    if client:
        try:
            # Get Indexes
            indices = client.cat.indices(format="json")
            
            # Key Metrics
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total Indexes", len(indices))
            with m2:
                total_docs = sum([int(i.get('docs.count', 0)) for i in indices])
                st.metric("Total Documents", total_docs)
            with m3:
                st.metric("Status", "Healthy", delta="Online")

            st.markdown("### 🗂️ Active Indexes")
            if indices:
                df = pd.DataFrame(indices)
                st.dataframe(
                    df[['index', 'health', 'status', 'docs.count', 'store.size']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No indexes found.")

            st.markdown("---")
            
            # Create Index Section
            st.subheader("✨ Create New Index")
            with st.form("create_index_form"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    new_index_name = st.text_input("Index Name", placeholder="e.g., products, logs-2024")
                with c2:
                    st.write("") # Spacer
                    st.write("") 
                    create_submitted = st.form_submit_button("Create Index", type="primary")
                
                if create_submitted and new_index_name:
                    try:
                        if not client.indices.exists(index=new_index_name):
                            # Basic settings/mappings
                            body = {
                                'settings': {'index': {'number_of_shards': 1, 'number_of_replicas': 1}},
                                'mappings': {
                                    'properties': {
                                        'name': {'type': 'text'},
                                        'category': {'type': 'keyword'},
                                        'created_at': {'type': 'date'}
                                    }
                                }
                            }
                            client.indices.create(index=new_index_name, body=body)
                            st.success(f"Index `{new_index_name}` created successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning(f"Index `{new_index_name}` already exists.")
                    except Exception as e:
                        st.error(f"Creation failed: {e}")

        except Exception as e:
            st.error(f"Could not fetch stats: {e}")
    else:
        st.info("Please configure the connection in the sidebar.")

# --- Tab 2: Data Entry (Insert Documents) ---
with tabs[1]:
    st.subheader("📝 Add Data")
    
    if client:
        try:
            indices_list = [i['index'] for i in client.cat.indices(format="json")]
        except:
            indices_list = []
            
        if not indices_list:
            st.warning("No indexes available. Create one in the Dashboard tab first.")
        else:
            selected_index = st.selectbox("Select Target Index", indices_list)
            
            with st.form("data_entry_form"):
                st.markdown("#### Document Details")
                d1, d2 = st.columns(2)
                with d1:
                    name = st.text_input("Item Name", placeholder="MacBook Pro 16")
                    category = st.selectbox("Category", ["Electronics", "Books", "Clothing", "Home", "Other"])
                with d2:
                    price = st.number_input("Price ($)", min_value=0.0, step=0.01, value=999.00)
                    in_stock = st.checkbox("In Stock", value=True)
                
                description = st.text_area("Description", placeholder="Product details...")
                
                submitted = st.form_submit_button("Insert Document", type="primary")
                
                if submitted:
                    doc = {
                        'name': name,
                        'category': category,
                        'price': price,
                        'in_stock': in_stock,
                        'description': description,
                        'created_at': time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    }
                    
                    try:
                        resp = client.index(index=selected_index, body=doc)
                        st.balloons()
                        st.success(f"Document added! ID: `{resp['_id']}`")
                    except Exception as e:
                        st.error(f"Insert failed: {e}")
    else:
        st.info("Connect to OpenSearch first.")

# --- Tab 3: Search Explorer ---
with tabs[2]:
    st.subheader("🔍 Search Explorer")
    
    if client:
        try:
            indices_list = [i['index'] for i in client.cat.indices(format="json")]
            s_index = st.selectbox("Search in Index", indices_list, key="search_idx")
        except:
            indices_list = []
            s_index = None
            
        search_query = st.text_input("Search Query", placeholder="Type to search...", key="search_box")
        
        if search_query and s_index:
            try:
                # Simple Match Query
                query = {
                    "query": {
                        "multi_match": {
                            "query": search_query,
                            "fields": ["name^2", "description", "category"]
                        }
                    }
                }
                
                res = client.search(index=s_index, body=query)
                hits = res['hits']['hits']
                count = res['hits']['total']['value']
                
                st.markdown(f"**Found {count} results**")
                
                for hit in hits:
                    source = hit['_source']
                    with st.container():
                        st.markdown(f"""
                        <div style="padding: 1rem; background-color: white; border-radius: 8px; border: 1px solid #f0f0f0; margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4 style="margin: 0; color: #1f2937;">{source.get('name', 'Unknown')}</h4>
                                <span style="background-color: #e0e7ff; color: #4338ca; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.8rem;">
                                    ${source.get('price', 0)}
                                </span>
                            </div>
                            <p style="color: #6b7280; font-size: 0.9rem; margin-top: 0.5rem;">{source.get('description', '')}</p>
                            <div style="margin-top: 0.5rem; font-size: 0.8rem; color: #9ca3af;">
                                ID: {hit['_id']} | Category: {source.get('category')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Search error: {e}")
    else:
        st.info("Connect to check your data.")

# --- Tab 4: Settings ---
with tabs[3]:
    st.subheader("🛠️ Advanced Settings")
    st.write("Current Configuration:")
    st.code(f"""
    OPENSEARCH_URL={env_url}
    AWS_REGION={os.getenv('AWS_REGION', 'us-east-1')}
    """, language="bash")
    
    if st.button("Reload Configuration"):
        load_config()
        st.success("Reloaded environment variables.")
