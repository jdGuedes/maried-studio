"use client";

import {
  CalendarDays,
  ChevronRight,
  Download,
  ExternalLink,
  Gem,
  LoaderCircle,
  MoreVertical,
  Pencil,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import {
  AnimatePresence,
  motion,
} from "motion/react";

import Image from "next/image";

import Link from "next/link";

import {
  useRouter,
  useSearchParams,
} from "next/navigation";

import {
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Pagination,
} from "@/components/pagination/pagination";

import {
  deleteProduct,
  getProduct,
  getProducts,
  ProductsApiError,
  renameProduct,
  type Product,
} from "@/lib/products";

import {
  getTotalPages,
  normalizePage,
} from "@/lib/pagination";


// ==========================================================
// CATEGORIAS
// ==========================================================

const categories = [
  {
    value: "",
    label: "Todas",
  },
  {
    value: "EARRING",
    label: "Brincos",
  },
  {
    value: "NECKLACE",
    label: "Colares",
  },
  {
    value: "RING",
    label: "Anéis",
  },
  {
    value: "BRACELET",
    label: "Pulseiras",
  },
  {
    value: "ANKLET",
    label: "Tornozeleiras",
  },
];


// ==========================================================
// DATA
// ==========================================================

function formatDate(
  value: string
) {
  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day:
        "2-digit",

      month:
        "2-digit",

      year:
        "numeric",
    }
  ).format(
    new Date(
      value
    )
  );
}


// ==========================================================
// PAGE
// ==========================================================

export default function ProductsPage() {
  return (
    <Suspense
      fallback={
        <ProductsLoading />
      }
    >
      <ProductsContent />
    </Suspense>
  );
}


function ProductsLoading() {
  return (
    <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto flex min-h-[420px] max-w-[1240px] items-center justify-center">
        <LoaderCircle
          size={32}
          className="animate-spin text-[var(--maried-gold)]"
        />
      </div>
    </main>
  );
}


function ProductsContent() {
  const router =
    useRouter();

  const searchParams =
    useSearchParams();

  const page =
    normalizePage(
      searchParams.get(
        "page"
      )
    );

  const search =
    searchParams.get(
      "q"
    ) ?? "";

  const category =
    searchParams.get(
      "category"
    ) ?? "";

  const startDate =
    searchParams.get(
      "start_date"
    ) ?? "";

  const endDate =
    searchParams.get(
      "end_date"
    ) ?? "";

  const searchTimer =
    useRef<number | null>(
      null
    );

  const [
    products,
    setProducts,
  ] = useState<Product[]>(
    []
  );


  const [
    loading,
    setLoading,
  ] = useState(
    true
  );


  const [
    count,
    setCount,
  ] = useState(
    0
  );


  const [
    error,
    setError,
  ] = useState<string | null>(
    null
  );


  const [
    selectedProduct,
    setSelectedProduct,
  ] = useState<Product | null>(
    null
  );


  const [
    loadingProduct,
    setLoadingProduct,
  ] = useState(
    false
  );


  const [
    openMenuId,
    setOpenMenuId,
  ] = useState<string | null>(
    null
  );


  const [
    renameTarget,
    setRenameTarget,
  ] = useState<Product | null>(
    null
  );


  const [
    renameValue,
    setRenameValue,
  ] = useState(
    ""
  );


  const [
    deleteTarget,
    setDeleteTarget,
  ] = useState<Product | null>(
    null
  );


  const [
    saving,
    setSaving,
  ] = useState(
    false
  );


  const totalPages =
    getTotalPages(
      count
    );


  const updateUrl =
    useCallback(
      (
        updates: Record<string, string | null>,
        nextPage = 1
      ) => {
        const params =
          new URLSearchParams(
            searchParams.toString()
          );

        Object.entries(
          updates
        ).forEach(
          ([
            key,
            value,
          ]) => {
            if (value) {
              params.set(
                key,
                value
              );
            } else {
              params.delete(
                key
              );
            }
          }
        );

        if (nextPage > 1) {
          params.set(
            "page",
            String(
              nextPage
            )
          );
        } else {
          params.delete(
            "page"
          );
        }

        const query =
          params.toString();

        router.push(
          query
            ? `/pecas?${query}`
            : "/pecas",
          {
            scroll:
              false,
          }
        );
      },
      [
        router,
        searchParams,
      ]
    );


  // ========================================================
  // LOAD
  // ========================================================

  const loadProducts =
    useCallback(
      async () => {

        setLoading(
          true
        );

        setError(
          null
        );


        try {

          const data =
            await getProducts({
              q:
                search,

              category,

              startDate:
                startDate ||
                undefined,

              endDate:
                endDate ||
                undefined,

              page,
            });


          setProducts(
            data.results
          );

          setCount(
            data.count
          );

        } catch (error) {

          if (
            error instanceof ProductsApiError &&
            error.status === 404 &&
            page > 1
          ) {
            updateUrl(
              {},
              1
            );

            return;
          }

          console.error(
            "Erro ao carregar peças:",
            error
          );


          setError(
            error instanceof Error
              ? error.message
              : "Não foi possível carregar suas peças."
          );

        } finally {

          setLoading(
            false
          );

        }

      },
      [
        search,
        category,
        startDate,
        endDate,
        page,
        updateUrl,
      ]
    );


  // ========================================================
  // BUSCA COM PEQUENO DEBOUNCE
  // ========================================================

  useEffect(() => {

    const timer =
      window.setTimeout(
        () => {
          void loadProducts();
        },
        350
      );


    return () => {
      window.clearTimeout(
        timer
      );
    };

  }, [
    loadProducts,
  ]);


  useEffect(() => {
    return () => {
      if (searchTimer.current) {
        window.clearTimeout(
          searchTimer.current
        );
      }
    };
  }, []);


  function scheduleSearch(
    value: string
  ) {
    if (searchTimer.current) {
      window.clearTimeout(
        searchTimer.current
      );
    }

    searchTimer.current =
      window.setTimeout(
        () => {
          updateUrl(
            {
              q:
                value.trim() ||
                null,
            },
            1
          );
        },
        350
      );
  }


  // ========================================================
  // DETALHE
  // ========================================================

  async function openProduct(
    productId: string
  ) {

    setLoadingProduct(
      true
    );


    try {

      const data =
        await getProduct(
          productId
        );


      setSelectedProduct(
        data
      );

    } catch (error) {

      console.error(
        "Erro ao abrir peça:",
        error
      );

    } finally {

      setLoadingProduct(
        false
      );

    }
  }


  // ========================================================
  // RENOMEAR
  // ========================================================

  async function confirmRename() {

    if (
      !renameTarget ||
      !renameValue.trim()
    ) {
      return;
    }


    setSaving(
      true
    );


    try {

      const updated =
        await renameProduct(
          renameTarget.id,
          renameValue.trim()
        );


      setProducts(
        (
          current
        ) =>
          current.map(
            (
              product
            ) =>
              product.id ===
              updated.id
                ? {
                    ...product,

                    name:
                      updated.name,
                  }
                : product
          )
      );


      if (
        selectedProduct?.id ===
        updated.id
      ) {

        setSelectedProduct({
          ...selectedProduct,

          name:
            updated.name,
        });

      }


      setRenameTarget(
        null
      );


      setRenameValue(
        ""
      );

    } catch (error) {

      console.error(
        "Erro ao renomear peça:",
        error
      );

    } finally {

      setSaving(
        false
      );

    }
  }


  // ========================================================
  // EXCLUIR
  // ========================================================

  async function confirmDelete() {

    if (
      !deleteTarget
    ) {
      return;
    }


    setSaving(
      true
    );


    try {

      await deleteProduct(
        deleteTarget.id
      );


      if (
        selectedProduct?.id ===
        deleteTarget.id
      ) {
        setSelectedProduct(
          null
        );
      }


      setDeleteTarget(
        null
      );


      if (
        products.length === 1 &&
        page > 1
      ) {
        updateUrl(
          {},
          page - 1
        );
      } else {
        await loadProducts();
      }

    } catch (error) {

      console.error(
        "Erro ao excluir peça:",
        error
      );

    } finally {

      setSaving(
        false
      );

    }
  }


  // ========================================================
  // RENDER
  // ========================================================

  return (
    <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">

      <div className="mx-auto max-w-[1240px]">

        {/* =================================================
            CABEÇALHO
        ================================================= */}

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">

          <div>

            <h1 className="text-[30px] font-semibold tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[36px]">
              Minhas peças
            </h1>


            <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
              Gerencie suas peças e acesse
              todas as imagens já criadas.
            </p>

          </div>


          <Link
            href="/criar"

            className="flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] px-5 text-sm font-medium text-white"
          >

            <Plus
              size={
                17
              }
            />

            Nova peça

          </Link>

        </div>


        {/* =================================================
            FILTROS
        ================================================= */}

        <section className="maried-card mt-7 p-4">

          <div className="grid gap-3 lg:grid-cols-[1fr_190px_160px_160px]">

            {/* BUSCA */}

            <div className="relative">

              <Search
                size={
                  16
                }

                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"
              />


              <input
                key={
                  search
                }

                defaultValue={
                  search
                }

                onChange={(
                  event
                ) => {
                  scheduleSearch(
                    event.target.value
                  );
                }}

                placeholder="Buscar peça..."

                className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-10 pr-4 text-sm outline-none focus:border-[var(--maried-gold)]"
              />

            </div>


            {/* CATEGORIA */}

            <select
              value={
                category
              }

              onChange={(
                event
              ) => {
                updateUrl(
                  {
                    category:
                      event.target.value ||
                      null,
                  },
                  1
                );
              }}

              className="h-11 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-sm outline-none focus:border-[var(--maried-gold)]"
            >

              {categories.map(
                (
                  item
                ) => (

                  <option
                    key={
                      item.value
                    }

                    value={
                      item.value
                    }
                  >
                    {
                      item.label
                    }
                  </option>

                )
              )}

            </select>


            {/* INÍCIO */}

            <label className="relative">

              <CalendarDays
                size={
                  15
                }

                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"
              />


              <input
                type="date"

                value={
                  startDate
                }

              onChange={(
                event
              ) => {
                  updateUrl(
                    {
                      start_date:
                        event.target.value ||
                        null,
                    },
                    1
                  );
                }}

                className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-9 pr-2 text-xs outline-none focus:border-[var(--maried-gold)]"
              />

            </label>


            {/* FIM */}

            <label className="relative">

              <CalendarDays
                size={
                  15
                }

                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--maried-caramel)]"
              />


              <input
                type="date"

                value={
                  endDate
                }

              onChange={(
                event
              ) => {
                  updateUrl(
                    {
                      end_date:
                        event.target.value ||
                        null,
                    },
                    1
                  );
                }}

                className="h-11 w-full rounded-xl border border-[var(--maried-sand)] bg-white pl-9 pr-2 text-xs outline-none focus:border-[var(--maried-gold)]"
              />

            </label>

          </div>


          {(search ||
            category ||
            startDate ||
            endDate) ? (

            <button
              type="button"

              onClick={() => {
                updateUrl(
                  {
                    q:
                      null,
                    category:
                      null,
                    start_date:
                      null,
                    end_date:
                      null,
                  },
                  1
                );
              }}

              className="mt-3 flex items-center gap-1 text-xs font-medium text-[var(--maried-gold)]"
            >

              <X
                size={
                  13
                }
              />

              Limpar filtros

            </button>

          ) : null}

        </section>


        {/* =================================================
            ERRO
        ================================================= */}

        {error ? (

          <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
            {
              error
            }
          </div>

        ) : null}


        {/* =================================================
            GRID
        ================================================= */}

        {loading ? (

          <div className="mt-8 flex min-h-[300px] items-center justify-center">

            <LoaderCircle
              size={
                30
              }

              className="animate-spin text-[var(--maried-gold)]"
            />

          </div>

        ) : products.length >
          0 ? (

          <>
          <section className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">

            {products.map(
              (
                product,
                index
              ) => (

                <motion.article
                  key={
                    product.id
                  }

                  initial={{
                    opacity:
                      0,

                    y:
                      8,
                  }}

                  animate={{
                    opacity:
                      1,

                    y:
                      0,
                  }}

                  transition={{
                    delay:
                      index *
                      0.035,
                  }}

                  className="relative overflow-visible rounded-[18px] border border-[var(--maried-sand)] bg-white"
                >

                  {/* IMAGEM */}

                  <button
                    type="button"

                    onClick={() => {
                      void openProduct(
                        product.id
                      );
                    }}

                    className="relative block aspect-square w-full overflow-hidden rounded-t-[17px] bg-[var(--maried-cream)]"
                  >

                    {product.original_image_url ? (

                      <Image
                        src={
                          product.original_image_url
                        }

                        alt={
                          product.name ||
                          "Peça"
                        }

                        fill

                        unoptimized

                        className="object-contain p-3 transition-transform duration-300 hover:scale-[1.02]"
                      />

                    ) : (

                      <div className="flex h-full items-center justify-center">

                        <Gem
                          size={
                            40
                          }

                          strokeWidth={
                            1.1
                          }

                          className="text-[var(--maried-gold)]"
                        />

                      </div>

                    )}

                  </button>


                  {/* CONTEÚDO */}

                  <div className="p-3">

                    <div className="flex items-start justify-between gap-2">

                      <div className="min-w-0">

                        <h2 className="truncate text-sm font-semibold text-[var(--maried-espresso)]">
                          {product.name ||
                            "Peça sem nome"}
                        </h2>


                        <p className="mt-1 text-[10px] text-[var(--maried-cocoa)]">
                          {
                            product.category_label
                          }
                        </p>

                      </div>


                      {/* MENU */}

                      <div className="relative">

                        <button
                          type="button"

                          onClick={() => {

                            setOpenMenuId(
                              openMenuId ===
                                product.id
                                ? null
                                : product.id
                            );

                          }}

                          className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-[var(--maried-cream)]"
                        >

                          <MoreVertical
                            size={
                              16
                            }
                          />

                        </button>


                        {openMenuId ===
                        product.id ? (

                          <div className="absolute right-0 top-9 z-30 w-44 rounded-xl border border-[var(--maried-sand)] bg-white p-1.5 shadow-[0_15px_40px_rgba(73,53,45,0.15)]">

                            <button
                              type="button"

                              onClick={() => {

                                setRenameTarget(
                                  product
                                );

                                setRenameValue(
                                  product.name
                                );

                                setOpenMenuId(
                                  null
                                );

                              }}

                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs hover:bg-[var(--maried-cream)]"
                            >

                              <Pencil
                                size={
                                  14
                                }
                              />

                              Renomear

                            </button>


                            <button
                              type="button"

                              onClick={() => {

                                void openProduct(
                                  product.id
                                );

                                setOpenMenuId(
                                  null
                                );

                              }}

                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs hover:bg-[var(--maried-cream)]"
                            >

                              <Sparkles
                                size={
                                  14
                                }
                              />

                              Ver resultados

                            </button>


                            <button
                              type="button"

                              onClick={() => {

                                setDeleteTarget(
                                  product
                                );

                                setOpenMenuId(
                                  null
                                );

                              }}

                              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
                            >

                              <Trash2
                                size={
                                  14
                                }
                              />

                              Excluir peça

                            </button>

                          </div>

                        ) : null}

                      </div>

                    </div>


                    <div className="mt-4 flex items-center justify-between">

                      <div>

                        <div className="text-[10px] text-[var(--maried-caramel)]">
                          {
                            product.generations_count
                          }{" "}
                          {product.generations_count ===
                          1
                            ? "criação"
                            : "criações"}
                        </div>


                        <div className="mt-1 text-[9px] text-[var(--maried-caramel)]">
                          {
                            formatDate(
                              product.created_at
                            )
                          }
                        </div>

                      </div>


                      <button
                        type="button"

                        onClick={() => {
                          void openProduct(
                            product.id
                          );
                        }}

                        className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--maried-soft-gold)] text-[var(--maried-gold)]"
                      >

                        <ChevronRight
                          size={
                            16
                          }
                        />

                      </button>

                    </div>

                  </div>

                </motion.article>

              )
            )}

          </section>

          <Pagination
            page={
              page
            }

            totalPages={
              totalPages
            }

            loading={
              loading
            }

            onPageChange={(
              nextPage
            ) => {
              updateUrl(
                {},
                nextPage
              );
            }}
          />

          </>

        ) : (

          <div className="maried-card mt-7 flex min-h-[320px] flex-col items-center justify-center px-6 text-center">

            <Gem
              size={
                38
              }

              className="text-[var(--maried-gold)]"
            />


            <h2 className="mt-5 text-sm font-semibold">
              Nenhuma peça encontrada
            </h2>


            <p className="mt-2 max-w-sm text-xs leading-5 text-[var(--maried-cocoa)]">
              Cadastre uma nova peça ou
              ajuste os filtros para encontrar
              itens já cadastrados.
            </p>


            <Link
              href="/criar"

              className="mt-5 flex h-10 items-center gap-2 rounded-xl bg-[var(--maried-gold)] px-4 text-xs font-medium text-white"
            >

              <Plus
                size={
                  15
                }
              />

              Nova peça

            </Link>

          </div>

        )}

      </div>


      {/* ===================================================
          DETALHE DA PEÇA
      =================================================== */}

      <AnimatePresence>

        {selectedProduct ||
        loadingProduct ? (

          <motion.div
            initial={{
              opacity:
                0,
            }}

            animate={{
              opacity:
                1,
            }}

            exit={{
              opacity:
                0,
            }}

            className="fixed inset-0 z-[100] flex items-end justify-center bg-black/25 p-0 backdrop-blur-sm sm:items-center sm:p-6"
          >

            <motion.div
              initial={{
                opacity:
                  0,

                y:
                  30,
              }}

              animate={{
                opacity:
                  1,

                y:
                  0,
              }}

              exit={{
                opacity:
                  0,

                y:
                  20,
              }}

              className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-t-[24px] bg-[var(--maried-ivory)] p-5 shadow-2xl sm:rounded-[24px] sm:p-6"
            >

              {loadingProduct ? (

                <div className="flex min-h-[350px] items-center justify-center">

                  <LoaderCircle
                    size={
                      30
                    }

                    className="animate-spin text-[var(--maried-gold)]"
                  />

                </div>

              ) : selectedProduct ? (

                <>
                  <div className="flex items-start justify-between gap-4">

                    <div>

                      <h2 className="text-2xl font-semibold tracking-[-0.03em]">
                        {selectedProduct.name ||
                          "Peça sem nome"}
                      </h2>


                      <p className="mt-1 text-xs text-[var(--maried-cocoa)]">
                        {
                          selectedProduct.category_label
                        }{" "}
                        • cadastrada em{" "}
                        {
                          formatDate(
                            selectedProduct.created_at
                          )
                        }
                      </p>

                    </div>


                    <button
                      type="button"

                      onClick={() => {
                        setSelectedProduct(
                          null
                        );
                      }}

                      className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white"
                    >

                      <X
                        size={
                          17
                        }
                      />

                    </button>

                  </div>


                  <div className="mt-6 grid gap-6 lg:grid-cols-[280px_1fr]">

                    {/* ORIGINAL */}

                    <div>

                      <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--maried-caramel)]">
                        Foto original
                      </div>


                      <div className="relative mt-3 aspect-square overflow-hidden rounded-[18px] bg-[var(--maried-cream)]">

                        {selectedProduct.original_image_url ? (

                          <Image
                            src={
                              selectedProduct.original_image_url
                            }

                            alt={
                              selectedProduct.name
                            }

                            fill

                            unoptimized

                            className="object-contain p-4"
                          />

                        ) : (

                          <div className="flex h-full items-center justify-center">

                            <Gem
                              size={
                                40
                              }

                              className="text-[var(--maried-gold)]"
                            />

                          </div>

                        )}

                      </div>


                      <Link
                        href={
                          `/criar?product=${selectedProduct.id}`
                        }

                        className="mt-3 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-coffee)] text-xs font-medium text-white"
                      >

                        <Sparkles
                          size={
                            15
                          }
                        />

                        Criar nova imagem

                      </Link>

                    </div>


                    {/* RESULTADOS */}

                    <div>

                      <div className="flex items-center justify-between">

                        <div>

                          <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-[var(--maried-caramel)]">
                            Resultados
                          </div>


                          <div className="mt-1 text-xs text-[var(--maried-cocoa)]">
                            {
                              selectedProduct.generations_count
                            }{" "}
                            imagens concluídas
                          </div>

                        </div>

                      </div>


                      {selectedProduct
                        .generations
                        .length >
                      0 ? (

                        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">

                          {selectedProduct
                            .generations
                            .map(
                              (
                                generation
                              ) => (

                                <div
                                  key={
                                    generation.id
                                  }

                                  className="overflow-hidden rounded-[16px] border border-[var(--maried-sand)] bg-white"
                                >

                                  <div className="relative aspect-square bg-[var(--maried-cream)]">

                                    {generation.image_url ? (

                                      <Image
                                        src={
                                          generation.image_url
                                        }

                                        alt={
                                          generation.mode_label
                                        }

                                        fill

                                        unoptimized

                                        className="object-cover"
                                      />

                                    ) : null}

                                  </div>


                                  <div className="p-3">

                                    <div className="text-xs font-medium">
                                      {
                                        generation.mode_label
                                      }
                                    </div>


                                    {generation.style_name ? (

                                      <div className="mt-1 text-[9px] text-[var(--maried-caramel)]">
                                        {
                                          generation.style_name
                                        }
                                      </div>

                                    ) : null}


                                    {generation.image_url ? (

                                      <div className="mt-3 flex gap-2">

                                        <a
                                          href={
                                            generation.image_url
                                          }

                                          target="_blank"

                                          rel="noreferrer"

                                          className="flex h-8 flex-1 items-center justify-center rounded-lg border border-[var(--maried-sand)] text-[var(--maried-coffee)]"
                                        >

                                          <ExternalLink
                                            size={
                                              13
                                            }
                                          />

                                        </a>


                                        <a
                                          href={
                                            generation.image_url
                                          }

                                          download

                                          className="flex h-8 flex-1 items-center justify-center rounded-lg bg-[var(--maried-gold)] text-white"
                                        >

                                          <Download
                                            size={
                                              13
                                            }
                                          />

                                        </a>

                                      </div>

                                    ) : null}

                                  </div>

                                </div>

                              )
                            )}

                        </div>

                      ) : (

                        <div className="mt-4 rounded-[18px] border border-dashed border-[var(--maried-sand)] p-8 text-center">

                          <Sparkles
                            size={
                              28
                            }

                            className="mx-auto text-[var(--maried-gold)]"
                          />


                          <p className="mt-3 text-xs text-[var(--maried-cocoa)]">
                            Esta peça ainda não possui
                            imagens geradas.
                          </p>

                        </div>

                      )}

                    </div>

                  </div>
                </>

              ) : null}

            </motion.div>

          </motion.div>

        ) : null}

      </AnimatePresence>


      {/* ===================================================
          MODAL RENOMEAR
      =================================================== */}

      <AnimatePresence>

        {renameTarget ? (

          <SimpleModal
            title="Renomear peça"

            onClose={() => {
              setRenameTarget(
                null
              );
            }}
          >

            <input
              value={
                renameValue
              }

              onChange={(
                event
              ) => {
                setRenameValue(
                  event.target.value
                );
              }}

              autoFocus

              maxLength={
                160
              }

              className="h-11 w-full rounded-xl border border-[var(--maried-sand)] px-3 text-sm outline-none focus:border-[var(--maried-gold)]"
            />


            <div className="mt-4 flex gap-3">

              <button
                type="button"

                onClick={() => {
                  setRenameTarget(
                    null
                  );
                }}

                className="h-11 flex-1 rounded-xl border border-[var(--maried-sand)] text-sm"
              >
                Cancelar
              </button>


              <button
                type="button"

                disabled={
                  saving ||
                  !renameValue.trim()
                }

                onClick={() => {
                  void confirmRename();
                }}

                className="h-11 flex-1 rounded-xl bg-[var(--maried-gold)] text-sm font-medium text-white disabled:opacity-50"
              >
                {saving
                  ? "Salvando..."
                  : "Salvar"}
              </button>

            </div>

          </SimpleModal>

        ) : null}

      </AnimatePresence>


      {/* ===================================================
          MODAL EXCLUIR
      =================================================== */}

      <AnimatePresence>

        {deleteTarget ? (

          <SimpleModal
            title="Excluir peça"

            onClose={() => {
              setDeleteTarget(
                null
              );
            }}
          >

            <p className="text-sm leading-6 text-[var(--maried-cocoa)]">
              A peça{" "}
              <strong>
                {deleteTarget.name ||
                  "sem nome"}
              </strong>{" "}
              será excluída permanentemente.
              Todas as imagens e criações
              vinculadas a ela também serão
              removidas. Esta ação não poderá
              ser desfeita.
            </p>


            <div className="mt-5 flex gap-3">

              <button
                type="button"

                onClick={() => {
                  setDeleteTarget(
                    null
                  );
                }}

                className="h-11 flex-1 rounded-xl border border-[var(--maried-sand)] text-sm"
              >
                Cancelar
              </button>


              <button
                type="button"

                disabled={
                  saving
                }

                onClick={() => {
                  void confirmDelete();
                }}

                className="h-11 flex-1 rounded-xl bg-red-600 text-sm font-medium text-white disabled:opacity-50"
              >
                {saving
                  ? "Excluindo..."
                  : "Excluir"}
              </button>

            </div>

          </SimpleModal>

        ) : null}

      </AnimatePresence>

    </main>
  );
}


// ==========================================================
// MODAL SIMPLES
// ==========================================================

type SimpleModalProps = {
  title: string;

  children:
    React.ReactNode;

  onClose:
    () => void;
};


function SimpleModal({
  title,
  children,
  onClose,
}: SimpleModalProps) {

  return (
    <motion.div
      initial={{
        opacity:
          0,
      }}

      animate={{
        opacity:
          1,
      }}

      exit={{
        opacity:
          0,
      }}

      className="fixed inset-0 z-[120] flex items-center justify-center bg-black/25 p-4 backdrop-blur-sm"
    >

      <motion.div
        initial={{
          opacity:
            0,

          scale:
            0.98,

          y:
            8,
        }}

        animate={{
          opacity:
            1,

          scale:
            1,

          y:
            0,
        }}

        exit={{
          opacity:
            0,

          scale:
            0.98,
        }}

        className="w-full max-w-md rounded-[20px] bg-white p-5 shadow-2xl"
      >

        <div className="mb-5 flex items-center justify-between">

          <h2 className="text-lg font-semibold">
            {
              title
            }
          </h2>


          <button
            type="button"

            onClick={
              onClose
            }

            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-[var(--maried-cream)]"
          >

            <X
              size={
                16
              }
            />

          </button>

        </div>


        {
          children
        }

      </motion.div>

    </motion.div>
  );
}
