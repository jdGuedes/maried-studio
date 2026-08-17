import type {
  ReactNode,
} from "react";

import {
  AppShell,
} from "@/components/layout/app-shell";


type ProfileLayoutProps = {
  children: ReactNode;
};


export default function ProfileLayout({
  children,
}: ProfileLayoutProps) {
  return (
    <AppShell>
      {children}
    </AppShell>
  );
}