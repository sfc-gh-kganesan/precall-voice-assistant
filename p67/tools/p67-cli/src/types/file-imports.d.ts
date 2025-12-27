// Type declarations for Bun file imports
// When importing with { type: 'file' }, Bun returns the file path as a string

declare module '*.md' {
    const filePath: string;
    export default filePath;
}

declare module '*.src' {
    const filePath: string;
    export default filePath;
}

declare module '*.txt' {
    const filePath: string;
    export default filePath;
}

declare module '*.json' {
    const filePath: string;
    export default filePath;
}
