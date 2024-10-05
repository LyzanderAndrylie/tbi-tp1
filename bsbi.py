import os
import pickle
import contextlib
import heapq
import time

from index import InvertedIndexReader, InvertedIndexWriter
from util import IdMap, QueryParser, DocumentParser, sort_diff_list, sort_intersect_list, sort_union_list
from compression import StandardPostings, VBEPostings, EliasGammaPostings

from porter2stemmer import Porter2Stemmer
import nltk
from nltk.corpus import stopwords


""" 
Ingat untuk install tqdm terlebih dahulu
pip intall tqdm
"""
from tqdm import tqdm

class BSBIIndex:
    """
    Attributes
    ----------
    term_id_map(IdMap): Untuk mapping terms ke termIDs
    doc_id_map(IdMap): Untuk mapping relative paths dari dokumen (misal,
                    /collection/0/gamma.txt) to docIDs
    data_path(str): Path ke data
    output_path(str): Path ke output index files
    postings_encoding: Lihat di compression.py, kandidatnya adalah StandardPostings,
                    VBEPostings, dsb.
    index_name(str): Nama dari file yang berisi inverted index
    """
    def __init__(self, data_path, output_path, postings_encoding, index_name = "main_index"):
        self.term_id_map = IdMap()
        self.doc_id_map = IdMap()
        self.data_path = data_path
        self.output_path = output_path
        self.index_name = index_name
        self.postings_encoding = postings_encoding

        # Untuk menyimpan nama-nama file dari semua intermediate inverted index
        self.intermediate_indices = []
        
        nltk.download('stopwords')
        self.stemmer = Porter2Stemmer()
        self.stopwords = set(stopwords.words('english'))
        self.document_parser = DocumentParser(self.stemmer, self.stopwords)
        
        # Menghindari doc id bernilai 0
        # Beberapa algoritma kompresi seperti Elias-Gamma memerlukan doc id berupa integer positif
        self.doc_id_map["[DUMMY]"]

    def save(self):
        """Menyimpan doc_id_map and term_id_map ke output directory via pickle"""

        with open(os.path.join(self.output_path, 'terms.dict'), 'wb') as f:
            pickle.dump(self.term_id_map, f)
        with open(os.path.join(self.output_path, 'docs.dict'), 'wb') as f:
            pickle.dump(self.doc_id_map, f)

    def load(self):
        """Memuat doc_id_map and term_id_map dari output directory"""

        with open(os.path.join(self.output_path, 'terms.dict'), 'rb') as f:
            self.term_id_map = pickle.load(f)
        with open(os.path.join(self.output_path, 'docs.dict'), 'rb') as f:
            self.doc_id_map = pickle.load(f)

    def start_indexing(self):
        """
        Base indexing code
        BAGIAN UTAMA untuk melakukan Indexing dengan skema BSBI (blocked-sort
        based indexing)

        Method ini scan terhadap semua data di collection, memanggil parse_block
        untuk parsing dokumen dan memanggil invert_write yang melakukan inversion
        di setiap block dan menyimpannya ke index yang baru.
        """
        # loop untuk setiap sub-directory di dalam folder collection (setiap block)
        for block_path in tqdm(sorted(next(os.walk(self.data_path))[1])):
            td_pairs = self.parsing_block(block_path)
            index_id = 'intermediate_index_'+block_path
            self.intermediate_indices.append(index_id)
            with InvertedIndexWriter(index_id, self.postings_encoding, path = self.output_path) as index:
                self.write_to_index(td_pairs, index)
                td_pairs = None
    
        self.save()

        with InvertedIndexWriter(self.index_name, self.postings_encoding, path = self.output_path) as merged_index:
            with contextlib.ExitStack() as stack:
                indices = [stack.enter_context(InvertedIndexReader(index_id, self.postings_encoding, path=self.output_path))
                               for index_id in self.intermediate_indices]
                self.merge_index(indices, merged_index)

    def parsing_block(self, block_path):
        """
        Lakukan parsing terhadap text file sehingga menjadi sequence of
        <termID, docID> pairs.

        Anda bisa menggunakan stemmer bahasa Inggris yang tersedia, seperti Porter Stemmer
        https://github.com/evandempsey/porter2-stemmer

        Untuk membuang stopwords, Anda dapat menggunakan library seperti NLTK.

        Untuk "sentence segmentation" dan "tokenization", bisa menggunakan
        regex atau boleh juga menggunakan tools lain yang berbasis machine
        learning.

        Parameters
        ----------
        block_path : str
            Relative Path ke directory yang mengandung text files untuk sebuah block.

            CATAT bahwa satu folder di collection dianggap merepresentasikan satu block.
            Konsep block di soal tugas ini berbeda dengan konsep block yang terkait
            dengan operating systems.

        Returns
        -------
        List[Tuple[Int, Int]]
            Returns all the td_pairs extracted from the block
            Mengembalikan semua pasangan <termID, docID> dari sebuah block (dalam hal
            ini sebuah sub-direktori di dalam folder collection)

        Harus menggunakan self.term_id_map dan self.doc_id_map untuk mendapatkan
        termIDs dan docIDs. Dua variable ini harus persis untuk semua pemanggilan
        parse_block(...).
        """
        td_pairs = []
        
        collections_block_path = os.path.join(self.data_path, block_path)
        
        for filename in os.listdir(collections_block_path):
            file_path = os.path.join(collections_block_path, filename)
            tokens = self.document_parser.parse(file_path)
            td_pairs.extend([(self.term_id_map[token], self.doc_id_map[file_path]) for token in tokens])
        
        return td_pairs

    def write_to_index(self, td_pairs, index):
        """
        Melakukan inversion td_pairs (list of <termID, docID> pairs) dan
        menyimpan mereka ke index. Disini diterapkan konsep BSBI dimana 
        hanya di-mantain satu dictionary besar untuk keseluruhan block.
        Namun dalam teknik penyimpanannya digunakan srategi dari SPIMI
        yaitu penggunaan struktur data hashtable (dalam Python bisa
        berupa Dictionary)

        ASUMSI: td_pairs CUKUP di memori

        Parameters
        ----------
        td_pairs: List[Tuple[Int, Int]]
            List of termID-docID pairs
        index: InvertedIndexWriter
            Inverted index pada disk (file) yang terkait dengan suatu "block"
        """
        term_dict = {}
        for term_id, doc_id in td_pairs:
            if term_id not in term_dict:
                term_dict[term_id] = set()
            term_dict[term_id].add(doc_id)
        for term_id in sorted(term_dict.keys()):
            index.append(term_id, sorted(list(term_dict[term_id])))

    def merge_index(self, indices, merged_index):
        """
        Lakukan merging ke semua intermediate inverted indices menjadi
        sebuah single index.

        Ini adalah bagian yang melakukan EXTERNAL MERGE SORT

        Parameters
        ----------
        indices: List[InvertedIndexReader]
            A list of intermediate InvertedIndexReader objects, masing-masing
            merepresentasikan sebuah intermediate inveted index yang iterable
            di sebuah block.

        merged_index: InvertedIndexWriter
            Instance InvertedIndexWriter object yang merupakan hasil merging dari
            semua intermediate InvertedIndexWriter objects.
        """
        sort_by_term_id = lambda x: x[0]
        heap_iter = heapq.merge(*indices, key=sort_by_term_id)
        current_term_id, current_postings_list = next(heap_iter)
        
        for term_id, postings_list in heap_iter:
            if term_id == current_term_id:
                current_postings_list = sort_union_list(current_postings_list, postings_list)
            else:
                merged_index.append(current_term_id, current_postings_list)
                current_term_id = term_id
                current_postings_list = postings_list
        merged_index.append(current_term_id, current_postings_list)
        

    def boolean_retrieve(self, query):
        """
        Melakukan boolean retrieval untuk mengambil semua dokumen yang
        mengandung semua kata pada query. Lakukan pre-processing seperti
        yang telah dilakukan pada tahap indexing, kecuali *penghapusan stopwords*.

        Jika terdapat stopwords dalam query, return list kosong dan berikan pesan bahwa
        terdapat stopwords di dalam query.

        Parse query dengan class QueryParser. Ambil representasi postfix dari ekspresi
        untuk kemudian dievaluasi di method ini. Silakan baca pada URL di bawah untuk lebih lanjut.
        https://www.geeksforgeeks.org/evaluation-of-postfix-expression/

        Anda tidak wajib mengimplementasikan conjunctive queries optimization.

        Parameters
        ----------
        query: str
            Query tokens yang dipisahkan oleh spasi. Ini dapat mengandung operator
            himpunan AND, NOT, dan DIFF, serta tanda kurung untuk presedensi. 

            contoh: (universitas AND indonesia OR depok) DIFF ilmu AND komputer

        Returns
        ------
        List[str]
            Daftar dokumen terurut yang mengandung sebuah query tokens.
            Harus mengembalikan EMPTY LIST [] jika tidak ada yang match.

        JANGAN LEMPAR ERROR/EXCEPTION untuk terms yang TIDAK ADA di collection.
        """
        query_parser = QueryParser(query, self.stemmer, self.stopwords)
        
        if not query_parser.is_valid():
            return [], "Query mengandung stopwords"
        
        postfix_tokens = query_parser.infix_to_postfix()
        postings_stack = []
        
        self.load() # load saved term_id_map and doc_id_map
        
        with InvertedIndexReader(self.index_name, self.postings_encoding, self.output_path) as main_index:
            for token in postfix_tokens:
                if query_parser.token_is_term(token):
                    postings = main_index.get_postings_list(self.term_id_map[token])
                    postings_stack.append(postings)
                else:
                    postings2 = postings_stack.pop()
                    postings1 = postings_stack.pop()
                    
                    result = []
                    
                    if token == "AND":
                        result = sort_intersect_list(postings1, postings2)
                    if token == "OR":
                        result = sort_union_list(postings1, postings2)
                    if token == "DIFF":
                        result = sort_diff_list(postings1, postings2)
                    
                    postings_stack.append(result)
        
        result_postings_doc_id = postings_stack.pop()
        result_postings_doc_path = [self.doc_id_map[doc_id] for doc_id in result_postings_doc_id]
        
        return result_postings_doc_path


if __name__ == "__main__":
    # BSBI with VBEPostings
    start_time_vb = time.time_ns()
    
    BSBI_instance_vb = BSBIIndex(data_path = 'arxiv_collections', \
                              postings_encoding = VBEPostings, \
                              output_path = 'index_vb')
    BSBI_instance_vb.start_indexing() # memulai indexing!
    
    end_time_vb = time.time_ns()
    
    elapsed_time = end_time_vb - start_time_vb
    print(f"Elapsed time: {elapsed_time} nanoseconds")
    print(f"Elapsed time: {elapsed_time / 1e9} seconds")
    
    # BSBI with EliasGammaPostings
    start_time_eg = time.time_ns()
    
    BSBI_instance_eg = BSBIIndex(data_path = 'arxiv_collections', \
                              postings_encoding = EliasGammaPostings, \
                              output_path = 'index_eg')
    BSBI_instance_eg.start_indexing() # memulai indexing!
    
    end_time_eg = time.time_ns()
    
    elapsed_time = end_time_eg - start_time_eg
    print(f"Elapsed time: {elapsed_time} nanoseconds")
    print(f"Elapsed time: {elapsed_time / 1e9} seconds")
    