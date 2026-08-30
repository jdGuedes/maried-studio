import { CreationWizard } from "@/components/create/creation-wizard";
import { AppShell } from "@/components/layout/app-shell";

type CreatePageProps = {
  searchParams?:
    Promise<
      Record<
        string,
        string | string[] | undefined
      >
    >;
};

export default async function CreatePage({
  searchParams,
}: CreatePageProps) {
  const params =
    (await searchParams) ?? {};

  const rawProduct =
    params.product;

  const productId =
    Array.isArray(rawProduct)
      ? rawProduct[0] ?? null
      : rawProduct ?? null;

  return (
    <AppShell>
      <CreationWizard
        productId={productId}
      />
    </AppShell>
  );
}
