# Information Retrieval System

This project is part of the CSCE604135 - Information Retrieval course at the Faculty of Computer Science, Universitas Indonesia. It focuses on implementing inverted index with compression algorithms for boolean retrieval using the arXiv dataset. The project provides a fully functional boolean retrieval system.

## Features

- **Boolean Retrieval**: Supports search queries with logical operators such as AND, OR, and DIFF.
- **Inverted Index**: Implements an inverted index using blocked sort-based indexing (BSBI).
- **Compression**: Implements two compression techniques:
  - **Variable Byte Encoding** (byte-level encoding)
  - **Elias-Gamma Coding** (bit-level encoding)
- **Efficient Query Processing**: Processes complex queries efficiently, including handling parentheses to manage precedence.

## Folder Structure

- [`bsbi.py`](./bsbi.py): Main script for BSBI indexing
- [`compression.py`](./compression.py): Compression algorithms implementation
- [`index.py`](./index.py): Inverted index reader and writer implementation
- [`search.py`](./search.py): Boolean retrieval search example
- [`util.py`](./util.py): Utility functions
- [`/index_vb`](./index_vb/): Folder for Variable Byte Encoding index file
- [`/index_eg`](./index_eg/): Folder for Elias-Gamma Coding index file

## How To Run

1. Clone the repository:

    ```shell
    git clone https://github.com/LyzanderAndrylie/tbi-tp1
    ```

2. Install the required dependencies:

    ```shell
    pipenv install
    ```

3. Prepare the dataset by placing the documents in a folder. For example, see the `arxiv_collections` folder structure.

4. Run the indexing script:

    ```shell
    python bsbi.py
    ```

5. Run the query search engine:

    ```shell
    python search.py
    ```

## Documentations

- [`Tugas Pemrograman 1.pdf`](./docs/Tugas%20Pemrograman%201.pdf): Task description
- [`Laporan.pdf`](./docs/Laporan.pdf): Experiment result
