import os
import sys
import yaml
import json
import time
import zlib
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Import local modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
from build_dense_vectors import DenseVectorBuilder
from build_sparse_vectors import SparseVectorBuilder
from schema import LegalDocumentPayload

# Rich Seed Data for Ingestion
SEED_DATA = {
    "laws": [
        {
            "doc_id": "law-civ-197",
            "chunk_id": "law-civ-197-001",
            "source_type": "laws",
            "title": "民法第197條",
            "section_type": "民法債編",
            "topic": "侵權行為損害賠償請求權之消滅時效",
            "issue_tag": "消滅時效",
            "law_name": "民法",
            "article_no": "第197條",
            "effective_date": "2021-01-13",
            "version": "2021",
            "text": "因侵權行為所生之損害賠償請求權，自請求權人知有損害及賠償義務人時起，二年間不行使而消滅，自有侵權行為時起，逾十年者亦同。損害賠償之義務人，因侵權行為受利益，致被害人受損害者，於前項時效消滅後，仍應依關於不當得利之規定，返還其所受之利益於被害人。",
            "source_path": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=B0000001&flno=197"
        },
        {
            "doc_id": "law-civ-126",
            "chunk_id": "law-civ-126-001",
            "source_type": "laws",
            "title": "民法第126條",
            "section_type": "民法總則編",
            "topic": "短期消滅時效",
            "issue_tag": "消滅時效",
            "law_name": "民法",
            "article_no": "第126條",
            "effective_date": "1930-05-05",
            "version": "1930",
            "text": "利息、紅利、租金、贍養費、退職金及其他一年或不及一年之定期給付債權，其各期給付請求權，因五年間不行使而消滅。",
            "source_path": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=B0000001&flno=126"
        },
        {
            "doc_id": "law-admin-131",
            "chunk_id": "law-admin-131-001",
            "source_type": "laws",
            "title": "行政程序法第131條",
            "section_type": "行政程序法",
            "topic": "公法上請求權消滅時效",
            "issue_tag": "消滅時效",
            "law_name": "行政程序法",
            "article_no": "第131條",
            "effective_date": "2021-06-09",
            "version": "2021",
            "text": "公法上之請求權，於請求權人為行政機關時，除法律另有規定外，因五年間不行使而消滅；於請求權人為人民時，除法律另有規定外，因十年間不行使而消滅。公法上請求權，因時效完成而當然消滅。前項時效，因行政機關為實現該權利所為之行政處分而中斷。",
            "source_path": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=A0030055&flno=131"
        },
        {
            "doc_id": "law-labor-14",
            "chunk_id": "law-labor-14-001",
            "source_type": "laws",
            "title": "勞動基準法第14條",
            "section_type": "勞動基準法",
            "topic": "勞工無須預告終止勞動契約之情形",
            "issue_tag": "勞資爭議",
            "law_name": "勞動基準法",
            "article_no": "第14條",
            "effective_date": "2020-06-10",
            "version": "2020",
            "text": "有下列情形之一者，勞工得不經預告終止契約：一、雇主於訂立勞動契約時為虛偽之意思表示，使勞工誤信而有受損害之虞者。二、雇主、雇主家屬、雇主代理人對於勞工，實施暴行或有重大侮辱之行為者。三、契約所約定之工作，對於勞工健康有危害之虞，經通知雇主改善而無效果者。五、雇主不依勞動契約給付工作報酬，或對於按件計酬之勞工不供給充分之工作者。六、雇主違反勞動契約或勞工法令，致有損害勞工權益之虞者。勞工依前項第一款、第六款規定終止契約者，應自知悉其情形之日起，三十日內為之。",
            "source_path": "https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno=14"
        }
    ],
    "cases": [
        {
            "doc_id": "case-49-1730",
            "chunk_id": "case-49-1730-001",
            "source_type": "cases",
            "title": "最高法院49年台上字第1730號民事判例",
            "case_id": "49年台上字第1730號",
            "court_level": "最高法院",
            "effective_date": "1960-01-01",
            "topic": "相當於租金之不當得利時效",
            "issue_tag": "不當得利",
            "text": "租金之請求權因五年間不行使而消滅，民法第一百二十六條定有明文。無法律上之原因而獲得相當於租金之利益，致他人受損害時，如該他人之不當得利返還請求權已逾五年者，債務人自得就此部分為時效消滅之抗辯，蓋此種利益之本質仍為租金，時效應適用民法第126條規定，不適用民法第125條之十五年時效。",
            "source_path": "司法院判例公報"
        },
        {
            "doc_id": "case-474",
            "chunk_id": "case-474-001",
            "source_type": "cases",
            "title": "司法院釋字第474號解釋",
            "case_id": "釋字第474號",
            "court_level": "大法官會議",
            "effective_date": "1999-01-29",
            "topic": "公法上時效及類推適用",
            "issue_tag": "消滅時效",
            "text": "公務人員保險法及公務人員退休法等公法上請求權消滅時效，在法律未明文規定前，應類推適用民法消滅時效之規定。公法上請求權關係公法上法律關係之安定，非有法律依據，行政機關不得以命令限制人民權利之行使。行政程序法第131條嗣後已明確將人民公法請求權時效規定為十年，行政機關為五年。",
            "source_path": "司法院大法官解釋網站"
        },
        {
            "doc_id": "case-104-3",
            "chunk_id": "case-104-3-001",
            "source_type": "cases",
            "title": "最高法院104年度第3次民事庭會議決議",
            "case_id": "104年度第3次民事庭會議決議",
            "court_level": "最高法院",
            "effective_date": "2015-02-03",
            "topic": "借名登記返還請求權時效",
            "issue_tag": "借名登記",
            "text": "借名登記關係登記契約終止後，委託人請求返還登記財產之權利，其性質為類推適用委任關係之終止返還請求權或所有權返還請求權。此項返還請求權之消滅時效，因非屬於民法第126條至128條等短期時效之範疇，自應適用民法第一百二十五條一般消滅時效之規定，即自請求權可行使時起，因十五年間不行使而消滅。",
            "source_path": "最高法院民事庭決議公報"
        }
    ],
    "course_notes": [],
    "exam_bank": [
        {
            "doc_id": "exam-110-civil",
            "chunk_id": "exam-110-civil-001",
            "source_type": "exam_bank",
            "title": "110年司法官律師第一試民法第25題",
            "topic": "不當得利租金時效",
            "issue_tag": "消滅時效",
            "text": "甲無權占有乙所有之土地建屋居住，乙於甲占有八年後，起訴請求甲拆屋還地並返還不當得利。甲就超過五年之不當得利部分為時效消滅之抗辯，是否有理？依最高法院49年台上字第1730號判例，無權占有他人土地所受相當於租金之利益，其不當得利返還請求權之消滅時效為五年，故甲之時效抗辯有理由。",
            "source_path": "考選部國家考試題庫"
        }
    ]
}

def load_pipeline_transcripts(config):
    # Search for all generated JSON files in A:\processed_md\ and add them to course_notes
    processed_dir = config.get('paths', {}).get('processed_md_dir', "A:\\processed_md")
    transcripts = []
    
    if not os.path.exists(processed_dir):
        return transcripts
        
    for file in os.listdir(processed_dir):
        if file.endswith(".json"):
            json_path = os.path.join(processed_dir, file)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Create a chunk for the course note
                transcripts.append({
                    "doc_id": data["doc_id"],
                    "chunk_id": f"{data['doc_id']}-001",
                    "source_type": "course_notes",
                    "title": data["title"],
                    "topic": data.get("inferred_subject", "法律教材"),
                    "issue_tag": "逐字稿學術教材",
                    "text": data["cleaned_text"][:2000],  # Take a chunk of 2000 chars for demonstration
                    "source_path": data["source_path"]
                })
            except Exception as e:
                print(f"[Ingest Warning] Failed to read {file}: {e}")
                
    return transcripts

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    local_path = config['qdrant'].get('local_path')
    host = config['qdrant'].get('host', 'localhost')
    port = config['qdrant'].get('port', 6333)
    
    # Init vectors builders
    dense_builder = DenseVectorBuilder(config_path)
    sparse_builder = SparseVectorBuilder(config_path)
    
    # Init client
    if local_path:
        client = QdrantClient(path=local_path)
    else:
        client = QdrantClient(host=host, port=port)
        
    # Gather dynamic pipeline course notes
    pipeline_notes = load_pipeline_transcripts(config)
    SEED_DATA["course_notes"].extend(pipeline_notes)
    
    # Step 1: Update BM25 corpus stats
    print("Gathering corpus texts to update BM25 stats...")
    all_texts = []
    for col_name, docs in SEED_DATA.items():
        for doc in docs:
            all_texts.append(doc["text"])
            
    sparse_builder.update_corpus_stats(all_texts)
    print(f"BM25 Stats updated. Total documents in corpus: {sparse_builder.N}, Average length: {sparse_builder.avg_doc_len:.2f}")
    
    # Step 2: Vectorize and Upsert documents
    for col_name, docs in SEED_DATA.items():
        if not docs:
            print(f"Collection '{col_name}' has no documents to ingest.")
            continue
            
        print(f"\nVectorizing and Ingesting {len(docs)} documents into collection '{col_name}'...")
        
        points = []
        for doc in docs:
            text = doc["text"]
            
            # Generate dense embedding (Gemini API)
            dense_vector = dense_builder.get_embedding(text)
            
            # Generate sparse vector (BM25)
            sparse_vector_data = sparse_builder.get_sparse_vector(text)
            sparse_vector = models.SparseVector(
                indices=sparse_vector_data["indices"],
                values=sparse_vector_data["values"]
            )
            
            # Validate payload
            payload_validated = LegalDocumentPayload(
                doc_id=doc["doc_id"],
                chunk_id=doc["chunk_id"],
                source_type=doc["source_type"],
                title=doc["title"],
                section_type=doc.get("section_type"),
                topic=doc.get("topic"),
                issue_tag=doc.get("issue_tag"),
                law_name=doc.get("law_name"),
                article_no=doc.get("article_no"),
                case_id=doc.get("case_id"),
                court_level=doc.get("court_level"),
                effective_date=doc.get("effective_date"),
                version=doc.get("version"),
                language="zh-TW",
                review_status="approved",
                source_path=doc["source_path"],
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                text=text
            )
            
            # Form Qdrant point
            # Map index values correctly
            points.append(
                models.PointStruct(
                    id=zlib.crc32(doc["chunk_id"].encode('utf-8')) & 0xfffffff, # safe integer id
                    vector={
                        "": dense_vector, # default dense vector
                        config['vectors']['sparse']['name']: sparse_vector
                    },
                    payload=payload_validated.dict()
                )
            )
            
        # Upsert to Qdrant
        client.upsert(
            collection_name=col_name,
            points=points
        )
        print(f"Upserted {len(points)} points into '{col_name}' successfully!")
        
    print("\nIngestion completed! All documents successfully vectorized and uploaded.")

if __name__ == "__main__":
    main()
