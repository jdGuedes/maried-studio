import type {
  ReactNode,
} from "react";

import {
  AppShell,
} from "@/components/layout/app-shell";


type PecasLayoutProps = {
  children: ReactNode;
};


export default function PecasLayout({
  children,
}: PecasLayoutProps) {
  return (
    <AppShell>
      {children}
    </AppShell>
  );
}