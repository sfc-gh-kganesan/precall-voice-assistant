import type { Value } from './manifest';
/**
 * ValueManager is a class that manages the values of the config, looking
 * references up in a KV store and decrypting secrets if necessary.
 */
export class ValueManager {
  private kvMap: Map<string, string>;
  private secretMap: Map<string, string>;

  constructor() {
    this.kvMap = new Map<string, string>();
    // TODO: populate.

    this.secretMap = new Map<string, string>();
    // TODO: populate.
  }

  async get(value?: Value): Promise<string> {
    if (!value) {
      return '';
    }
    if (value.value) {
      return value.value;
    }
    if (value.valueRef) {
      return this.getValue(value.valueRef);
    }
    if (value.secretRef) {
      const secret = await this.getSecret(value.secretRef);
      const decryptedSecret = await this.decryptSecret(secret);
      return decryptedSecret;
    }
    throw new Error(`Invalid value: ${JSON.stringify(value)}`);
  }

  async getValue(valueRef: string): Promise<string> {
    const value = this.kvMap.get(valueRef);
    if (!value) {
      throw new Error(`Value not found: ${valueRef}`);
    }
    return value;
  }

  async getSecret(secretRef: string): Promise<string> {
    const secret = this.secretMap.get(secretRef);
    if (!secret) {
      throw new Error(`Secret not found: ${secretRef}`);
    }
    return secret;
  }

  async decryptSecret(secret: string): Promise<string> {
    // TODO: implement
    return secret;
  }
}
