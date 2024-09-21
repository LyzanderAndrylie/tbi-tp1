import array
from typing import Literal

class StandardPostings:
    """ 
    Class dengan static methods, untuk mengubah representasi postings list
    yang awalnya adalah List of integer, berubah menjadi sequence of bytes.
    Kita menggunakan Library array di Python.

    ASUMSI: postings_list untuk sebuah term MUAT di memori!

    Silakan pelajari:
        https://docs.python.org/3/library/array.html
    """

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        # Untuk yang standard, gunakan L untuk unsigned long, karena docID
        # tidak akan negatif. Dan kita asumsikan docID yang paling besar
        # cukup ditampung di representasi 4 byte unsigned.
        return array.array('L', postings_list).tobytes()

    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        decoded_postings_list = array.array('L')
        decoded_postings_list.frombytes(encoded_postings_list)
        return decoded_postings_list.tolist()


class VBEPostings:
    """ 
    Berbeda dengan StandardPostings, dimana untuk suatu postings list,
    yang disimpan di disk adalah sequence of integers asli dari postings
    list tersebut apa adanya.

    Pada VBEPostings, kali ini, yang disimpan adalah gap-nya, kecuali
    posting yang pertama. Barulah setelah itu di-encode dengan Variable-Byte
    Enconding algorithm ke bytestream.

    Contoh:
    postings list [34, 67, 89, 454] akan diubah dulu menjadi gap-based,
    yaitu [34, 33, 22, 365]. Barulah setelah itu di-encode dengan algoritma
    compression Variable-Byte Encoding, dan kemudian diubah ke bytesream.

    ASUMSI: postings_list untuk sebuah term MUAT di memori!

    """

    @staticmethod
    def encode(postings_list):
        """
        Encode postings_list menjadi stream of bytes (dengan Variable-Byte
        Encoding). JANGAN LUPA diubah dulu ke gap-based list, sebelum
        di-encode dan diubah ke bytearray.

        Parameters
        ----------
        postings_list: List[int]
            List of docIDs (postings)

        Returns
        -------
        bytes
            bytearray yang merepresentasikan urutan integer di postings_list
        """
        gap_list = [postings_list[0]]
        
        for current_num, next_num in zip(postings_list[:-1], postings_list[1:]):
            gap_list.append(next_num - current_num)
            
        vb_encode_bytestream = VBEPostings.vb_encode(gap_list)
        
        return bytes(vb_encode_bytestream)
    
    @staticmethod
    def vb_encode(list_of_numbers):
        """ 
        Melakukan encoding (tentunya dengan compression) terhadap
        list of numbers, dengan Variable-Byte Encoding
        """
        bytestream = bytearray()
        
        for number in list_of_numbers:
            num_bytes = VBEPostings.vb_encode_number(number)
            bytestream.extend(num_bytes)
        
        return bytestream

    @staticmethod
    def vb_encode_number(number):
        """
        Encodes a number using Variable-Byte Encoding
        Lihat buku teks kita!
        """
        num_bytes = bytearray()
        
        while True:
            num_bytes.insert(0, number % 128)
            
            if number < 128:
                break
            
            number = number // 128
            
        num_bytes[-1] += 128
        
        return num_bytes

    @staticmethod
    def decode(encoded_postings_list):
        """
        Decodes postings_list dari sebuah stream of bytes. JANGAN LUPA
        bytestream yang di-decode dari encoded_postings_list masih berupa
        gap-based list.

        Parameters
        ----------
        encoded_postings_list: bytes
            bytearray merepresentasikan encoded postings list sebagai keluaran
            dari static method encode di atas.

        Returns
        -------
        List[int]
            list of docIDs yang merupakan hasil decoding dari encoded_postings_list
        """
        gap_list = VBEPostings.vb_decode(encoded_postings_list)
        
        postings_list = [gap_list[0]]
        
        for gap in gap_list[1:]:
            postings_list.append(postings_list[-1] + gap)
        
        return postings_list

    @staticmethod
    def vb_decode(encoded_bytestream):
        """
        Decoding sebuah bytestream yang sebelumnya di-encode dengan
        variable-byte encoding.
        """
        numbers = []
        n = 0
        for byte in encoded_bytestream:
            if (byte < 128):
                n = 128 * n + byte
            else:
                n = 128 * n + byte - 128
                numbers.append(n)
                n = 0
        return numbers

class EliasGammaPostings:
    """
    Elias gamma code is a universal code encoding positive integers developed by Peter Elias.
    It is used most commonly when coding integers whose upper-bound cannot be determined beforehand.
    
    Source: https://en.wikipedia.org/wiki/Elias_gamma_coding
    """
    
    @staticmethod
    def encode(postings_list):
        gap_list = [postings_list[0]]
        
        for current_num, next_num in zip(postings_list[:-1], postings_list[1:]):
            gap_list.append(next_num - current_num)
        
        eg_encode_bytestream = EliasGammaPostings.eg_encode(gap_list)
        
        return bytes(eg_encode_bytestream)
    
    @staticmethod
    def eg_encode(list_of_numbers):
        bytestream = bytearray()
        bits_per_byte = 8
        last_bits = ''
        
        for number in list_of_numbers:
            num_bits = f'{last_bits}{EliasGammaPostings.eg_encode_number(number)}'
            last_bits = ''
            num_bytes = []
            
            for i in range(0, len(num_bits), bits_per_byte):
                if i+bits_per_byte > len(num_bits):
                    last_bits = num_bits[i:]
                else:
                    num_bytes.append(
                        EliasGammaPostings.bits_str_to_int(num_bits[i:i+bits_per_byte])
                    )
            
            bytestream.extend(num_bytes)
        
        # Add remaining last bit
        if last_bits:
            last_bits = EliasGammaPostings.padding_bits_str(last_bits, 'right')
            bytestream.append(EliasGammaPostings.bits_str_to_int(last_bits))
        
        return bytestream
    
    @staticmethod
    def eg_encode_number(number) -> str:
        bit_length = number.bit_length()
        num_binary = EliasGammaPostings.int_to_bits_str(number)
        power = "0" * (bit_length - 1)
        encoded = f'{power}{num_binary}'
        
        return encoded

    @staticmethod
    def decode(encoded_postings_list):
        gap_list = EliasGammaPostings.eg_decode(encoded_postings_list)
        
        postings_list = [gap_list[0]]
        
        for gap in gap_list[1:]:
            postings_list.append(postings_list[-1] + gap)
        
        return postings_list
    
    @staticmethod
    def eg_decode(encoded_bytestream):
        numbers = []
        
        current_number = 0
        power = 0
        remainder_bits = ''
        
        for byte in encoded_bytestream:
            bits_str = EliasGammaPostings.int_to_bits_str(byte)
            bits = EliasGammaPostings.padding_bits_str(bits_str, 'left')
            
            for bit in bits:
                if current_number == 0:
                    # Meet 0 before 1: Get N of 2^N
                    if bit == '0':
                        power += 1
                        
                    if bit == '1':
                        # Meet 1 after 0
                        if power > 0:
                            current_number = 1 << power
                        
                        # Meet 1 before 0
                        if power == 0:
                            numbers.append(EliasGammaPostings.bits_str_to_int(bit))
                # Met 1
                else:
                    # Get remainder bit str
                    if power != 0:
                        remainder_bits += bit
                        power -= 1
                        
                    # Add remainder to current_number = 2^N + remainder
                    if power == 0:
                        current_number += EliasGammaPostings.bits_str_to_int(remainder_bits)
                        numbers.append(current_number)
                        
                        current_number = 0
                        power = 0
                        remainder_bits = ''
        
        return numbers
    
    @staticmethod
    def bits_str_to_int(bits: str):
        if not bits:
            return 0
        
        return int(bits, 2)

    @staticmethod
    def int_to_bits_str(number: int):
        return bin(number)[2:]

    
    @staticmethod
    def padding_bits_str(bits_str: str, padding: Literal['left', 'right', 'none'] = 'none', padding_size = 8):
        if padding == 'none':
            return bits_str
        
        if padding == 'left':
            return f'{bits_str:0>{padding_size}}' 
        
        if padding == 'right':
            return f'{bits_str:0<{padding_size}}' 


if __name__ == '__main__':
    
    postings_list = [34, 67, 89, 454, 2345738]
    for Postings in [StandardPostings, EliasGammaPostings, EliasGammaPostings]:
        print(Postings.__name__)
        encoded_postings_list = Postings.encode(postings_list)
        print("byte hasil encode: ", encoded_postings_list)
        print("ukuran encoded postings: ", len(encoded_postings_list), "bytes")
        decoded_posting_list = Postings.decode(encoded_postings_list)
        print("hasil decoding: ", decoded_posting_list)
        assert decoded_posting_list == postings_list, "hasil decoding tidak sama dengan postings original"
        print()
