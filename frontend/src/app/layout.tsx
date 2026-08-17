import type {
  Metadata,
} from "next";

import {
  Inter,
} from "next/font/google";

import "./globals.css";

import {
  CreditWalletProvider,
} from "@/providers/credit-wallet-provider";

import {
  ProfileProvider,
} from "@/providers/profile-provider";


const inter =
  Inter({
    subsets: [
      "latin",
    ],

    display:
      "swap",
  });


export const metadata:
  Metadata = {
    title:
      "MARIED STUDIO",

    description:
      "Criação profissional de imagens para semijoias.",
  };


export default function RootLayout({
  children,
}: Readonly<{
  children:
    React.ReactNode;
}>) {

  return (
    <html
      lang="pt-BR"
    >
      <body
        suppressHydrationWarning
        className={
          inter.className
        }
      >

        <ProfileProvider>

          <CreditWalletProvider>

            {
              children
            }

          </CreditWalletProvider>

        </ProfileProvider>

      </body>
    </html>
  );
}