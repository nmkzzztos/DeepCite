---
id: "introduction"
title: "Introduction"
sidebar_position: 1
---
import { CitationProvider, Citation, References } from '@site/src/components/Citation/Citation';

<CitationProvider>
# Cryptography

is the practice and study of techniques for securing communication and data from adversaries <Citation id="cryptography" />. It involves the use of mathematical concepts and algorithms to protect information from unauthorized access, tampering, or interception.

## Key Concepts

**Encryption**: The process of converting plaintext (readable data) into ciphertext (coded text) to prevent unauthorized access.

$$
\text{Cryptography } \rightarrow \text{ mdr62ibq7OmtGq+oFWfDgQ==}
$$

**Decryption**: The process of converting ciphertext back into plaintext using the same cryptographic key. 

$$
\text{mdr62ibq7OmtGq+oFWfDgQ== } \rightarrow \text{ Cryptography} 
$$

**Keys**: Secret values used in encryption and decryption processes.

$$ 
\text{Ciphertext: y4Di0ct94kCgnK3nA7EF1g | Key: secret } \rightarrow \text{ Cryptography}
$$

**Hashing**: A process that converts data into a fixed-size value (hash) that is unique $ \sum_{i=1}^{n} i = \frac{n(n+1)}{2} $ and cannot be reversed, typically used for verifying data integrity.

5 - **Digital Signatures**: A method of associating a digital message with a signature, which can be verified by the recipient to ensure the message's authenticity and integrity.

$$ S(m) = s $$

6 - **Authentication**: Ensuring that the parties involved in communication are who they claim to be.

## Types of Cryptography

1. **Symmetric Cryptography**: Uses the same key for both encryption and decryption (e.g. AES, DES).

2. **Asymmetric Cryptography**: Uses a pair of keys (public and private) for encryption and decryption, where the public key is used for encryption and the private key is used for decryption (e.g. RSA, ECC).

3. **Hash Functions**: Convert data into a fixed-size value that is unique and cannot be reversed (e.g. SHA-256, MD5).

4. **Quantum Cryptography**: Uses quantum mechanics to secure communication (e.g. quantum key distribution, quantum random number generation).

<References />
</CitationProvider>
