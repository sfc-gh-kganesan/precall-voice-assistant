import type { Metadata } from 'next'
import { Roboto } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'
import { ChatContainer } from '@/components/chat/ChatContainer'

const roboto = Roboto({
  weight: ['400', '500', '700'],
  subsets: ['latin'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Support Intelligence Platform',
  description: 'AI-powered analytics for customer support teams',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={roboto.className}>
        <Providers>
          {children}
          <ChatContainer />
        </Providers>
      </body>
    </html>
  )
}
