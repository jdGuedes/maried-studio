import { CreationWizard } from "@/components/create/creation-wizard";
import { AppShell } from "@/components/layout/app-shell";

export default function CreatePage() {
  return (
    <AppShell>
      <CreationWizard />
    </AppShell>
  );
}