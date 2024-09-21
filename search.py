from bsbi import BSBIIndex
from compression import VBEPostings, EliasGammaPostings

# sebelumnya sudah dilakukan indexing
# BSBIIndex hanya sebagai abstraksi untuk index tersebut
BSBI_instance_vb = BSBIIndex(data_path = 'arxiv_collections', \
                          postings_encoding = VBEPostings, \
                          output_path = 'index_vb')

BSBI_instance_eg = BSBIIndex(data_path = 'arxiv_collections', \
                          postings_encoding = EliasGammaPostings, \
                          output_path = 'index_eg')

queries = ["(cosmological AND (quantum OR continuum)) AND geodesics"]

for instance in [BSBI_instance_vb, BSBI_instance_eg]:
    for query in queries:
        print(f"Class: {instance.__class__.__name__}")
        print("Query  : ", query)
        print("Results:")
        for doc in instance.boolean_retrieve(query):
            print(doc)
        print()