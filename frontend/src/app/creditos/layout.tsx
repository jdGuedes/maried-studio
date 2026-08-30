import type {
  ReactNode,
} from "react";

import {
  AppShell,
} from "@/components/layout/app-shell";


type CreditsLayoutProps = {
  children: ReactNode;
};


export default function CreditsLayout({
  children,
}: CreditsLayoutProps) {
  return (
    <AppShell>
      {children}
    </AppShell>
  );
}
