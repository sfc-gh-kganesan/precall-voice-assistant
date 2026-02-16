import { WebClient } from '@slack/web-api';

/**
 * Slack client singleton for posting messages
 */
let webClient: WebClient | null = null;

/**
 * Get or create the Slack Web API client
 */
export function getSlackClient(): WebClient | null {
    const botToken = process.env.SLACK_BOT_TOKEN;

    if (!botToken) {
        console.warn(
            '⚠️  SLACK_BOT_TOKEN not set - cannot post messages to Slack',
        );
        return null;
    }

    if (!webClient) {
        webClient = new WebClient(botToken);
    }

    return webClient;
}

/**
 * Result of posting a message (includes thread_ts for threading)
 */
export interface PostMessageResult {
    ok: boolean;
    ts?: string; // Message timestamp, used as thread_ts for replies
    channel?: string;
    error?: string;
}

/**
 * Post a message to a Slack channel
 */
export async function postMessage(
    channel: string,
    text: string,
    options?: {
        threadTs?: string; // Reply in thread
        blocks?: unknown[];
        mrkdwn?: boolean;
    },
): Promise<PostMessageResult> {
    const client = getSlackClient();
    if (!client) {
        return { ok: false, error: 'Slack client not configured' };
    }

    try {
        const result = await client.chat.postMessage({
            channel,
            text,
            thread_ts: options?.threadTs,
            blocks: options?.blocks as never,
            mrkdwn: options?.mrkdwn ?? true,
        });

        return {
            ok: result.ok ?? false,
            ts: result.ts,
            channel: result.channel,
        };
    } catch (error) {
        console.error('Failed to post Slack message:', error);
        return {
            ok: false,
            error: error instanceof Error ? error.message : 'Unknown error',
        };
    }
}

/**
 * Update an existing Slack message
 */
export async function updateMessage(
    channel: string,
    ts: string,
    text: string,
    options?: {
        blocks?: unknown[];
    },
): Promise<{ ok: boolean; error?: string }> {
    const client = getSlackClient();
    if (!client) {
        return { ok: false, error: 'Slack client not configured' };
    }

    try {
        const result = await client.chat.update({
            channel,
            ts,
            text,
            blocks: options?.blocks as never,
        });

        return { ok: result.ok ?? false };
    } catch (error) {
        console.error('Failed to update Slack message:', error);
        return {
            ok: false,
            error: error instanceof Error ? error.message : 'Unknown error',
        };
    }
}

/**
 * Add a reaction (emoji) to a message
 */
export async function addReaction(
    channel: string,
    ts: string,
    emoji: string,
): Promise<{ ok: boolean; error?: string }> {
    const client = getSlackClient();
    if (!client) {
        return { ok: false, error: 'Slack client not configured' };
    }

    try {
        const result = await client.reactions.add({
            channel,
            timestamp: ts,
            name: emoji,
        });

        return { ok: result.ok ?? false };
    } catch (error) {
        // Ignore "already_reacted" errors
        if (
            error instanceof Error &&
            error.message.includes('already_reacted')
        ) {
            return { ok: true };
        }
        console.error('Failed to add reaction:', error);
        return {
            ok: false,
            error: error instanceof Error ? error.message : 'Unknown error',
        };
    }
}

/**
 * Remove a reaction from a message
 */
export async function removeReaction(
    channel: string,
    ts: string,
    emoji: string,
): Promise<{ ok: boolean; error?: string }> {
    const client = getSlackClient();
    if (!client) {
        return { ok: false, error: 'Slack client not configured' };
    }

    try {
        const result = await client.reactions.remove({
            channel,
            timestamp: ts,
            name: emoji,
        });

        return { ok: result.ok ?? false };
    } catch (error) {
        // Ignore "no_reaction" errors
        if (error instanceof Error && error.message.includes('no_reaction')) {
            return { ok: true };
        }
        console.error('Failed to remove reaction:', error);
        return {
            ok: false,
            error: error instanceof Error ? error.message : 'Unknown error',
        };
    }
}
