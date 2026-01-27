import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 12; // GCM standard
const AUTH_TAG_LENGTH = 16;

let encryptionKey: Buffer | null = null;

/**
 * Initialize the crypto module with an encryption key.
 * Must be called before encrypt/decrypt operations.
 * @param key Base64-encoded 32-byte key
 */
export function initCrypto(key: string): void {
    const keyBuffer = Buffer.from(key, 'base64');
    if (keyBuffer.length !== 32) {
        throw new Error(
            `Invalid encryption key length: expected 32 bytes, got ${keyBuffer.length}`,
        );
    }
    encryptionKey = keyBuffer;
}

/**
 * Check if the crypto module has been initialized.
 */
export function isCryptoInitialized(): boolean {
    return encryptionKey !== null;
}

function getKey(): Buffer {
    if (!encryptionKey) {
        throw new Error(
            'Crypto not initialized. Call initCrypto() with the encryption key first.',
        );
    }
    return encryptionKey;
}

/**
 * Encrypt a plaintext string using AES-256-GCM.
 * @param plaintext The string to encrypt
 * @returns Base64-encoded string containing iv + authTag + ciphertext
 */
export function encrypt(plaintext: string): string {
    const key = getKey();
    const iv = randomBytes(IV_LENGTH);
    const cipher = createCipheriv(ALGORITHM, key, iv);

    const encrypted = Buffer.concat([
        cipher.update(plaintext, 'utf8'),
        cipher.final(),
    ]);
    const authTag = cipher.getAuthTag();

    // Pack as: iv + authTag + ciphertext
    const packed = Buffer.concat([iv, authTag, encrypted]);
    return packed.toString('base64');
}

/**
 * Decrypt a ciphertext string using AES-256-GCM.
 * @param encoded Base64-encoded string containing iv + authTag + ciphertext
 * @returns The decrypted plaintext string
 */
export function decrypt(encoded: string): string {
    const key = getKey();
    const packed = Buffer.from(encoded, 'base64');

    if (packed.length < IV_LENGTH + AUTH_TAG_LENGTH) {
        throw new Error('Invalid ciphertext: too short');
    }

    const iv = packed.subarray(0, IV_LENGTH);
    const authTag = packed.subarray(IV_LENGTH, IV_LENGTH + AUTH_TAG_LENGTH);
    const ciphertext = packed.subarray(IV_LENGTH + AUTH_TAG_LENGTH);

    const decipher = createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    return Buffer.concat([
        decipher.update(ciphertext),
        decipher.final(),
    ]).toString('utf8');
}
