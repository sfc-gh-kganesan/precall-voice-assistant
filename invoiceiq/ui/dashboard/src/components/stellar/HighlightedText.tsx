import React from "react";

export interface HighlightedTextProps {
    text: string;
    searchString: string;
    style?: React.CSSProperties;
}

/**
 * Component that highlights matching portions of text with a yellow background
 * @param text - The full text to display
 * @param searchString - The string to highlight within the text
 * @param style - Optional additional styles to apply to the container
 */
export function HighlightedText(props: HighlightedTextProps) {
    const { text, searchString, style } = props;

    // If no search string or text, return the text as-is
    if (!searchString || !searchString.trim() || !text) {
        return <span style={style}>{text}</span>;
    }

    const normalizedSearch = searchString.toLowerCase().trim();
    const normalizedText = text.toLowerCase();

    // Find the index of the search string in the text (case-insensitive)
    const index = normalizedText.indexOf(normalizedSearch);

    // If no match found, return the text as-is
    if (index === -1) {
        return <span style={style}>{text}</span>;
    }

    // Split the text into parts: before match, match, after match
    const beforeMatch = text.substring(0, index);
    const match = text.substring(index, index + searchString.length);
    const afterMatch = text.substring(index + searchString.length);

    return (
        <span style={style}>
            {beforeMatch}
            <mark
                style={{
                    backgroundColor: "#fef08a",
                    color: "inherit",
                    padding: "0",
                    borderRadius: "2px",
                }}
            >
                {match}
            </mark>
            {afterMatch}
        </span>
    );
}

