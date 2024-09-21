from bsbi import BSBIIndex
from compression import VBEPostings, EliasGammaPostings
import time

# sebelumnya sudah dilakukan indexing
# BSBIIndex hanya sebagai abstraksi untuk index tersebut
BSBI_instance_vb = BSBIIndex(data_path = 'arxiv_collections', \
                          postings_encoding = VBEPostings, \
                          output_path = 'index_vb')

BSBI_instance_eg = BSBIIndex(data_path = 'arxiv_collections', \
                          postings_encoding = EliasGammaPostings, \
                          output_path = 'index_eg')

queries = [
    "(cosmological AND (quantum OR continuum)) AND geodesics",
    "((photon AND colliders AND (order OR accuracy)) OR (sparse AND (game OR theory) DIFF boson) OR (system AND matter AND (friction OR quantum))) DIFF (comsological OR rotation) AND ((photon AND colliders AND (order OR accuracy) AND (quark OR gluon) AND (production OR distribution)) OR (sparse AND (game OR theory) DIFF boson AND (graph OR proof)) OR (system AND matter AND (friction OR quantum) AND (fluid OR motion) AND (Earth OR Mars))) DIFF (cosmological OR rotation OR particle)"
]

for instance in [BSBI_instance_vb, BSBI_instance_eg]:
    for query in queries:
        start_time = time.perf_counter()
        
        print(f"Class: {instance.postings_encoding.__name__}")
        print("Query  : ", query)
        print("Results:")
        
        end_time = time.perf_counter()
        
        elapsed_time = end_time - start_time
        
        print(f"Elapsed time: {elapsed_time} seconds")
        
        for doc in instance.boolean_retrieve(query):
            print(doc)
        print()
        