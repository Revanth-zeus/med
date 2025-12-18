import weaviate
from weaviate.classes.config import Property, DataType, Configure
from weaviate.classes.query import MetadataQuery
from weaviate.classes.init import Auth
from typing import List, Dict, Optional, Callable
import uuid
import os

class RAGService:
    """RAG service using Weaviate vector database"""
    
    def __init__(self, weaviate_url: str = None):
        """Initialize RAG service"""
        
        self.client = None
        self.embedding_model = None
        self.is_cloud = False
        
        # Check for Weaviate Cloud credentials
        cloud_url = os.getenv("WEAVIATE_URL", "").strip()
        cloud_api_key = os.getenv("WEAVIATE_API_KEY", "").strip()
        
        print(f"\n{'='*60}")
        print(f"📧 RAG Service Initialization")
        print(f"{'='*60}")
        print(f"   WEAVIATE_URL set: {bool(cloud_url)}")
        print(f"   WEAVIATE_API_KEY set: {bool(cloud_api_key)}")
        if cloud_url:
            print(f"   URL: {cloud_url[:50]}...")
        if cloud_api_key:
            print(f"   API Key: {cloud_api_key[:20]}...")
        
        if cloud_url and cloud_api_key:
            # Clean URL
            cloud_url = cloud_url.rstrip('/')
            if not cloud_url.startswith('http'):
                cloud_url = 'https://' + cloud_url
            
            print(f"\n🌐 Attempting Weaviate Cloud connection: {cloud_url}")
            
            # Try connection methods in order
            connection_success = False
            last_error = None
            
            # Method 1: connect_to_weaviate_cloud (recommended for v4)
            if not connection_success:
                try:
                    print("   Method 1: connect_to_weaviate_cloud...")
                    self.client = weaviate.connect_to_weaviate_cloud(
                        cluster_url=cloud_url,
                        auth_credentials=Auth.api_key(cloud_api_key)
                    )
                    self.is_cloud = True
                    connection_success = True
                    print("   ✅ Connected via connect_to_weaviate_cloud")
                except Exception as e:
                    last_error = str(e)
                    print(f"   ❌ Method 1 failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Method 2: connect_to_wcs
            if not connection_success:
                try:
                    print("   Method 2: connect_to_wcs...")
                    self.client = weaviate.connect_to_wcs(
                        cluster_url=cloud_url,
                        auth_credentials=Auth.api_key(cloud_api_key)
                    )
                    self.is_cloud = True
                    connection_success = True
                    print("   ✅ Connected via connect_to_wcs")
                except Exception as e:
                    last_error = str(e)
                    print(f"   ❌ Method 2 failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Method 3: WeaviateClient direct (v3 style with v4)
            if not connection_success:
                try:
                    print("   Method 3: connect_to_custom...")
                    # Extract host from URL
                    host = cloud_url.replace("https://", "").replace("http://", "")
                    
                    self.client = weaviate.connect_to_custom(
                        http_host=host,
                        http_port=443,
                        http_secure=True,
                        grpc_host=host,
                        grpc_port=443,
                        grpc_secure=True,
                        auth_credentials=Auth.api_key(cloud_api_key)
                    )
                    self.is_cloud = True
                    connection_success = True
                    print("   ✅ Connected via connect_to_custom")
                except Exception as e:
                    last_error = str(e)
                    print(f"   ❌ Method 3 failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            if not connection_success:
                print(f"\n❌ ALL WEAVIATE CONNECTION METHODS FAILED")
                print(f"   Last error: {last_error}")
                print(f"   URL: {cloud_url}")
                print(f"   API Key length: {len(cloud_api_key)}")
                self.client = None
        else:
            # Try local Weaviate
            try:
                print("\n🏠 Trying local Weaviate...")
                self.client = weaviate.connect_to_local(
                    host="localhost",
                    port=8080
                )
                self.is_cloud = False
                print("   ✅ Connected to local Weaviate")
            except Exception as e:
                print(f"   ⚠️ Local Weaviate not available: {e}")
                self.client = None
        
        # Initialize embedding model if client connected
        if self.client:
            try:
                print("\n📦 Loading embedding model...")
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("   ✅ Embedding model loaded")
                self._create_schema()
                print(f"\n{'='*60}")
                print(f"✅ RAG SERVICE READY")
                print(f"   Mode: {'Cloud' if self.is_cloud else 'Local'}")
                print(f"{'='*60}\n")
            except Exception as e:
                print(f"   ❌ Embedding model error: {e}")
                import traceback
                traceback.print_exc()
                self.embedding_model = None
        else:
            print(f"\n{'='*60}")
            print(f"⚠️ RAG SERVICE NOT AVAILABLE")
            print(f"   Document upload/search features disabled")
            print(f"{'='*60}\n")
    
    def _create_schema(self):
        """Create Weaviate schema for hospital documents"""
        if not self.client:
            return
            
        try:
            if self.client.collections.exists("HospitalDocument"):
                print("✅ HospitalDocument collection exists")
                return
            
            self.client.collections.create(
                name="HospitalDocument",
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="filename", data_type=DataType.TEXT),
                    Property(name="file_id", data_type=DataType.TEXT),
                    Property(name="mime_type", data_type=DataType.TEXT),
                    Property(name="chunk_index", data_type=DataType.INT),
                    Property(name="section", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none()
            )
            print("✅ Created HospitalDocument collection")
        except Exception as e:
            print(f"⚠️ Schema creation note: {e}")
    
    def index_document(
        self, 
        file_id: str, 
        filename: str, 
        mime_type: str, 
        chunks: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> int:
        """Index document chunks into Weaviate"""
        if not self.client or not self.embedding_model:
            print("⚠️ RAG service not available for indexing")
            return 0
        
        try:
            collection = self.client.collections.get("HospitalDocument")
            indexed_count = 0
            
            valid_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
            total_chunks = len(valid_chunks)
            
            if total_chunks == 0:
                print(f"⚠️ No valid chunks to index for {filename}")
                return 0
            
            print(f"\n📝 Indexing {total_chunks} chunks from {filename}...")
            
            BATCH_SIZE = 32
            
            for batch_idx in range(0, total_chunks, BATCH_SIZE):
                batch_chunks = valid_chunks[batch_idx:batch_idx + BATCH_SIZE]
                batch_num = (batch_idx // BATCH_SIZE) + 1
                
                progress_pct = int((batch_idx / total_chunks) * 100)
                print(f"   📄 [{progress_pct}%] Processing batch {batch_num}...")
                
                if progress_callback:
                    progress_callback(batch_idx, total_chunks, f"Batch {batch_num}")
                
                try:
                    batch_embeddings = self.embedding_model.encode(
                        batch_chunks,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        batch_size=32
                    )
                    
                    for j, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                        section = self._detect_section(chunk)
                        
                        collection.data.insert(
                            properties={
                                "content": chunk,
                                "filename": filename,
                                "file_id": file_id,
                                "mime_type": mime_type,
                                "chunk_index": batch_idx + j,
                                "section": section
                            },
                            vector=embedding.tolist()
                        )
                        indexed_count += 1
                        
                except Exception as batch_error:
                    print(f"   ⚠️ Batch error: {batch_error}")
                    continue
            
            if progress_callback:
                progress_callback(total_chunks, total_chunks, "Complete!")
            
            print(f"✅ Indexed {indexed_count}/{total_chunks} chunks from {filename}")
            return indexed_count
            
        except Exception as e:
            print(f"❌ Error indexing document: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _detect_section(self, text: str) -> str:
        """Simple section detection"""
        text_lower = text.lower()
        if 'section' in text_lower or 'chapter' in text_lower:
            import re
            match = re.search(r'section\s+(\d+\.?\d*)', text_lower)
            if match:
                return f"Section {match.group(1)}"
        return "General"
    
    def search(self, query: str, limit: int = 5, file_filter: Optional[str] = None) -> List[Dict]:
        """Semantic search across indexed documents"""
        if not self.client or not self.embedding_model:
            return []
        
        try:
            query_embedding = self.embedding_model.encode(query).tolist()
            collection = self.client.collections.get("HospitalDocument")
            
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=limit,
                return_metadata=MetadataQuery(distance=True)
            )
            
            results = []
            for item in response.objects:
                results.append({
                    "content": item.properties.get("content", ""),
                    "filename": item.properties.get("filename", ""),
                    "file_id": item.properties.get("file_id", ""),
                    "section": item.properties.get("section", "General"),
                    "chunk_index": item.properties.get("chunk_index", 0),
                    "relevance_score": 1 - item.metadata.distance if item.metadata.distance else 0.0
                })
            
            return results
            
        except Exception as e:
            print(f"Error searching: {e}")
            return []
    
    def delete_document(self, file_id: str) -> int:
        """Delete all chunks for a specific file"""
        if not self.client:
            return 0
            
        try:
            collection = self.client.collections.get("HospitalDocument")
            from weaviate.classes.query import Filter
            
            result = collection.data.delete_many(
                where=Filter.by_property("file_id").equal(file_id)
            )
            
            deleted_count = result.matches if hasattr(result, 'matches') else 0
            print(f"✅ Deleted {deleted_count} chunks for file {file_id}")
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting document: {e}")
            return 0
    
    def get_all_indexed_files(self) -> List[Dict]:
        """Get list of all indexed files"""
        if not self.client:
            return []
            
        try:
            collection = self.client.collections.get("HospitalDocument")
            
            try:
                response = collection.aggregate.over_all(group_by="filename")
                
                files = []
                for group in response.groups:
                    files.append({
                        "filename": group.grouped_by.value,
                        "file_id": "",
                        "chunk_count": group.total_count
                    })
                return files
                
            except Exception as agg_error:
                print(f"Aggregation fallback: {agg_error}")
                files_dict = {}
                count = 0
                for item in collection.iterator():
                    count += 1
                    if count > 1000:
                        break
                    filename = item.properties.get("filename", "Unknown")
                    file_id = item.properties.get("file_id", "")
                    
                    if filename not in files_dict:
                        files_dict[filename] = {
                            "filename": filename,
                            "file_id": file_id,
                            "chunk_count": 0
                        }
                    files_dict[filename]["chunk_count"] += 1
                
                return list(files_dict.values())
                
        except Exception as e:
            print(f"Error getting indexed files: {e}")
            return []
    
    def file_exists(self, filename: str) -> bool:
        """Check if a file is already indexed"""
        if not self.client:
            return False
            
        try:
            collection = self.client.collections.get("HospitalDocument")
            from weaviate.classes.query import Filter
            
            response = collection.query.fetch_objects(
                filters=Filter.by_property("filename").equal(filename),
                limit=1
            )
            return len(response.objects) > 0
        except Exception as e:
            print(f"Error checking file: {e}")
            return False
    
    def delete_by_filename(self, filename: str) -> int:
        """Delete all chunks for a specific filename"""
        if not self.client:
            return 0
            
        try:
            collection = self.client.collections.get("HospitalDocument")
            from weaviate.classes.query import Filter
            
            result = collection.data.delete_many(
                where=Filter.by_property("filename").equal(filename)
            )
            
            deleted_count = result.matches if hasattr(result, 'matches') else 0
            print(f"✅ Deleted {deleted_count} chunks for {filename}")
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting by filename: {e}")
            return 0
    
    def close(self):
        """Close Weaviate client connection"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
