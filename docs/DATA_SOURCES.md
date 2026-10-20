# KrishiRAG Data Sources Register

**CSE 473 · SIH25076 · AI-Based Farmer Query Support and Advisory System**  
**Theme:** Agriculture, FoodTech & Rural Development  
**Last Updated:** 2026-10-20  

---

## Authoritative Public Agricultural Knowledge Sources

KrishiRAG relies strictly on vetted, authoritative agricultural publications from government departments, state agricultural universities (SAUs), and the Indian Council of Agricultural Research (ICAR). No synthetic or scraped unverified advice is permitted in the RAG corpus.

---

### Registered Primary Documents

#### 1. Crop Production Guide — Rice (Oryza sativa L.)
- **Publisher:** Tamil Nadu Agricultural University (TNAU) & Department of Agriculture, Government of Tamil Nadu
- **Document Title:** Crop Production Guide — Rice (Oryza sativa L.)
- **Source URL:** `https://tnagriculture.in/dashboard/CPG/01_Rice.pdf`
- **File Name:** `tnau_crop_production_guide_rice.pdf`
- **Local Path:** `data/sources/tnau_crop_production_guide_rice.pdf`
- **SHA-256 Checksum:** `97c933318298b249cf74bbb737f66a614687c8f45e4e8353ac4c04e17b2987e2`
- **File Size:** 674,700 bytes (75 pages)
- **License / Terms:** Public Government Agricultural Advisory Publication (Open Access Extension Material)
- **Key Agronomic Topics Covered:**
  - Climate and soil requirements
  - Nursery management (wet nursery, dry nursery, mat nursery / SRI)
  - Transplanted and direct-seeded rice techniques
  - Site-Specific Nutrient Management (SSNM) and biofertilizers (Azospirillum, Phosphobacteria)
  - Weed management, critical irrigation stages, and water budgeting
  - Major pests (Brown Planthopper, Stem Borer, Gall Midge) and bio-control recommendations
  - Diseases (Blast, Bacterial Leaf Blight, Sheath Blight) and integrated management

#### 2. Ready Reckoner: Package of Practices of Crops
- **Publisher:** National Food Security Mission (NFSM), Crops Division, Department of Agriculture, Cooperation & Farmers Welfare, Ministry of Agriculture & Farmers Welfare, Government of India
- **Document Title:** Ready Reckoner: Package of Practices of Crops
- **Source URL:** `https://nfsm.gov.in/ReadyReckoner/NFSM_Package.pdf`
- **File Name:** `nfsm_package_of_practices_ready_reckoner.pdf`
- **Local Path:** `data/sources/nfsm_package_of_practices_ready_reckoner.pdf`
- **SHA-256 Checksum:** `4f34dea88da335f82e54cd3f21d0a6ae17b723764b5dd266db288a3394355b64`
- **File Size:** 2,104,517 bytes
- **License / Terms:** Government of India Open Agricultural Data / National Advisory
- **Key Agronomic Topics Covered:**
  - Standard seed rates and spacing for cereal, pulse, and oilseed crops
  - Recommended high-yielding and disease-resistant cultivars
  - State-wise package of practices across Indian agro-climatic zones
  - Fertilizer doses (NPK + micronutrients like Zinc and Boron)
  - Integrated pest and disease management schedules

---

## Ingestion Provenance & Verification Protocol

1. **Integrity Verification:** Every ingested PDF is hashed via SHA-256 prior to processing.
2. **Deduplication:** A database unique constraint on `documents.checksum_sha256` prevents redundant ingestion.
3. **Chunk Lineage:** Chunks retain document ID, page numbers, detected section headings, and a deterministic UUID v5 vector ID.
4. **Attribution:** Citations link directly back to the verified document checksum and page number.
