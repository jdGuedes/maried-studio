"use client";

import {
  ResultModeStep,
  type GenerationMode,
} from "./result-mode-step";

import {
  StyleStep,
} from "./style-step";

import {
  ConfirmationStep,
} from "./confirmation-step";

import {
  ApiError,
  createGeneration,
  createProduct,
  getActiveGeneration,
  getGeneration,
  getModelReferences,
  getSceneTemplates,
} from "@/lib/api";

import {
  ImagePreparationError,
  prepareImage,
} from "@/lib/image-preparation";

import {
  getProduct,
  ProductsApiError,
  type Product as ExistingProduct,
} from "@/lib/products";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";

import {
  useBillingAccess,
} from "@/providers/billing-access-provider";

import type {
  Generation,
  ModelReference,
  ProductCategory,
  SceneTemplate,
} from "@/types/api";

import {
  ArrowRight,
  Camera,
  Check,
  Download,
  ImagePlus,
  LoaderCircle,
  Plus,
  RotateCcw,
  Sparkles,
  UploadCloud,
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
} from "next/navigation";

import {
  ChangeEvent,
  DragEvent,
  useEffect,
  useRef,
  useState,
} from "react";


// =========================================================
// CATEGORIAS
// =========================================================

const categories = [
  {
    value: "EARRING",
    label: "Brinco",
  },
  {
    value: "NECKLACE",
    label: "Colar",
  },
  {
    value: "RING",
    label: "Anel",
  },
  {
    value: "BRACELET",
    label: "Pulseira",
  },
  {
    value: "ANKLET",
    label: "Tornozeleira",
  },
] as const;


const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;


const GENERATION_POLL_INTERVAL_MS =
  5000;


const GENERATION_POLL_MAX_ATTEMPTS =
  72;


function isValidUuid(
  value:
    string
) {
  return UUID_PATTERN.test(
    value
  );
}


function getCategoryLabel(
  value:
    string
) {
  return (
    categories.find(
      (category) =>
        category.value === value
    )?.label ?? value
  );
}


function revokePreviewUrl(
  value:
    string | null
) {
  if (
    value?.startsWith(
      "blob:"
    )
  ) {
    URL.revokeObjectURL(
      value
    );
  }
}


function isPendingGeneration(
  generation:
    Generation
) {
  return [
    "CREDIT_RESERVED",
    "PROCESSING",
  ].includes(
    generation.status
  );
}


function getPendingGenerationCopy(
  generation:
    Generation
) {
  if (
    generation.status ===
    "CREDIT_RESERVED"
  ) {
    return {
      title:
        "Sua criação entrou na fila",
      description:
        "Vamos começar em instantes. Você pode continuar navegando pelo MARIED Studio.",
    };
  }

  if (
    generation.status ===
    "PROCESSING"
  ) {
    return {
      title:
        "Estamos criando sua imagem",
      description:
        "Esse processo pode levar alguns minutinhos. Você não precisa ficar nesta página enquanto preparamos sua criação.",
    };
  }

  return {
    title:
      "Não conseguimos concluir esta criação.",
    description:
      "Seu crédito foi devolvido quando aplicável. Você pode tentar novamente.",
  };
}


// =========================================================
// WIZARD
// =========================================================

type WizardStep =
  | 1
  | 2
  | 3
  | 4
  | 5;


type CreationSource =
  | "NEW_PRODUCT"
  | "EXISTING_PRODUCT";


type CreationWizardProps = {
  productId?:
    string | null;
};


const stepLabels = [
  {
    step: 1,
    label: "Sua peça",
  },
  {
    step: 2,
    label: "Resultado",
  },
  {
    step: 3,
    label: "Visual",
  },
  {
    step: 4,
    label: "Confirmação",
  },
] as const;


// =========================================================
// COMPONENTE
// =========================================================

export function CreationWizard({
  productId = null,
}: CreationWizardProps) {
  const router =
    useRouter();

  const creationSource:
    CreationSource =
    productId
      ? "EXISTING_PRODUCT"
      : "NEW_PRODUCT";

  const inputRef =
    useRef<HTMLInputElement>(
      null
    );

  const cameraInputRef =
    useRef<HTMLInputElement>(
      null
    );

  const generationPollAttempts =
    useRef(
      0
    );


  // =======================================================
  // CARTEIRA GLOBAL
  // =======================================================

  const {
    availableCredits,
    refreshWallet,
    setWalletFromGeneration,
  } =
    useCreditWallet();


  const {
    loading:
      loadingBillingAccess,
    canOperateStudio,
    accessMessage,
    accessCtaLabel,
  } =
    useBillingAccess();


  // =======================================================
  // ETAPA
  // =======================================================

  const [
    step,
    setStep,
  ] = useState<WizardStep>(
    1
  );


  // =======================================================
  // RESULTADO
  // =======================================================

  const [
    generationMode,
    setGenerationMode,
  ] = useState<GenerationMode | null>(
    null
  );


  // =======================================================
  // TEMPLATES
  // =======================================================

  const [
    sceneTemplates,
    setSceneTemplates,
  ] = useState<SceneTemplate[]>(
    []
  );


  const [
    selectedTemplateId,
    setSelectedTemplateId,
  ] = useState<string | null>(
    null
  );


  const [
    loadingTemplates,
    setLoadingTemplates,
  ] = useState(
    false
  );


  const [
    templatesError,
    setTemplatesError,
  ] = useState<string | null>(
    null
  );


  // =======================================================
  // MODELOS
  // =======================================================

  const [
    modelReferences,
    setModelReferences,
  ] = useState<ModelReference[]>(
    []
  );


  const [
    selectedModelReferenceId,
    setSelectedModelReferenceId,
  ] = useState<string | null>(
    null
  );


  const [
    loadingModelReferences,
    setLoadingModelReferences,
  ] = useState(
    false
  );


  const [
    modelReferencesError,
    setModelReferencesError,
  ] = useState<string | null>(
    null
  );


  // =======================================================
  // PRODUTO
  // =======================================================

  const [
    productName,
    setProductName,
  ] = useState(
    ""
  );


  const [
    category,
    setCategory,
  ] = useState<ProductCategory>(
    "EARRING"
  );


  const [
    file,
    setFile,
  ] = useState<File | null>(
    null
  );


  const [
    preview,
    setPreview,
  ] = useState<string | null>(
    null
  );


  const [
    dragging,
    setDragging,
  ] = useState(
    false
  );


  const [
    existingProduct,
    setExistingProduct,
  ] = useState<ExistingProduct | null>(
    null
  );


  const [
    loadingExistingProduct,
    setLoadingExistingProduct,
  ] = useState(
    Boolean(productId)
  );


  const [
    existingProductError,
    setExistingProductError,
  ] = useState<string | null>(
    null
  );


  // =======================================================
  // PREPARAÇÃO AUTOMÁTICA
  // =======================================================

  const [
    preparingImage,
    setPreparingImage,
  ] = useState(
    false
  );


  const [
    imagePreparationMessage,
    setImagePreparationMessage,
  ] = useState<string | null>(
    null
  );


  // =======================================================
  // PRODUTO CRIADO
  // =======================================================

  const [
    createdProductId,
    setCreatedProductId,
  ] = useState<string | null>(
    null
  );


  // =======================================================
  // GERAÇÃO
  // =======================================================

  const [
    isGenerating,
    setIsGenerating,
  ] = useState(
    false
  );


  const [
    generationError,
    setGenerationError,
  ] = useState<string | null>(
    null
  );


  const [
    generation,
    setGeneration,
  ] = useState<Generation | null>(
    null
  );


  const [
    loadingActiveGeneration,
    setLoadingActiveGeneration,
  ] = useState(
    true
  );


  // =======================================================
  // IDEMPOTÊNCIA
  // =======================================================

  const [
    idempotencyKey,
    setIdempotencyKey,
  ] = useState<string | null>(
    null
  );


  // =======================================================
  // TEMPLATE SELECIONADO
  // =======================================================

  const selectedTemplate =
    sceneTemplates.find(
      (template) =>
        template.id ===
        selectedTemplateId
    ) ?? null;


  const selectedModelReference =
    modelReferences.find(
      (modelReference) =>
        modelReference.id ===
        selectedModelReferenceId
    ) ?? null;


  function modeUsesSceneTemplate(
    mode:
      GenerationMode | null
  ) {
    return mode ===
      "INSTAGRAM";
  }


  function modeUsesModelReference(
    mode:
      GenerationMode | null
  ) {
    return (
      mode ===
        "BODY_DETAIL" ||
      mode ===
        "MODEL"
    );
  }


  // =======================================================
  // PREVIEW
  // =======================================================

  useEffect(() => {
    return () => {
      revokePreviewUrl(
        preview
      );
    };
  }, [preview]);


  useEffect(() => {
    if (
      loadingBillingAccess ||
      canOperateStudio
    ) {
      return;
    }

    router.replace(
      "/assinatura"
    );
  }, [
    loadingBillingAccess,
    canOperateStudio,
    router,
  ]);


  // =======================================================
  // CRIAR CHAVE DE IDEMPOTÊNCIA
  // =======================================================

  function createIdempotencyKey() {
    if (
      typeof crypto !==
        "undefined" &&
      typeof crypto.randomUUID ===
        "function"
    ) {
      return crypto.randomUUID();
    }

    return [
      Date.now(),
      Math.random()
        .toString(36)
        .slice(2),
    ].join("-");
  }


  // =======================================================
  // RESET DA GERAÇÃO
  // =======================================================

  function resetGenerationState() {
    setGeneration(
      null
    );

    setGenerationError(
      null
    );

    setIdempotencyKey(
      null
    );

    generationPollAttempts.current =
      0;
  }


  useEffect(() => {
    let active =
      true;

    void getActiveGeneration()
      .then(
        (
          activeGeneration
        ) => {
          if (
            !active
          ) {
            return;
          }

          if (
            activeGeneration &&
            isPendingGeneration(
              activeGeneration
            )
          ) {
            setGeneration(
              activeGeneration
            );

            setGenerationError(
              null
            );

            setStep(
              5
            );
          }
        }
      )
      .catch(
        (
          error
        ) => {
          console.error(
            "Erro ao consultar criação ativa:",
            error
          );
        }
      )
      .finally(
        () => {
          if (
            active
          ) {
            setLoadingActiveGeneration(
              false
            );
          }
        }
      );

    return () => {
      active =
        false;
    };
  }, []);


  useEffect(() => {
    if (
      !generation ||
      !isPendingGeneration(
        generation
      )
    ) {
      return;
    }

    if (
      generationPollAttempts.current >=
      GENERATION_POLL_MAX_ATTEMPTS
    ) {
      setGenerationError(
        "A geração continua sendo processada. Você pode acompanhar o resultado em Minhas criações."
      );

      return;
    }

    const timer =
      window.setTimeout(
        () => {
          generationPollAttempts.current +=
            1;

          void getGeneration(
            generation.id
          )
            .then(
              async (
                latestGeneration
              ) => {
                setGeneration(
                  latestGeneration
                );

                if (
                  latestGeneration.status ===
                  "COMPLETED"
                ) {
                  setWalletFromGeneration(
                    latestGeneration.available_credits
                  );

                  await refreshWallet();
                  setGenerationError(
                    null
                  );
                }

                if (
                  latestGeneration.status ===
                  "FAILED"
                ) {
                  await refreshWallet();
                  setGenerationError(
                    latestGeneration.error_message ||
                    "Não foi possível concluir esta geração. Seu crédito foi devolvido quando aplicável."
                  );
                }
              }
            )
            .catch(
              (
                error
              ) => {
                console.error(
                  "Erro ao consultar status da geração:",
                  error
                );
              }
            );
        },
        GENERATION_POLL_INTERVAL_MS
      );

    return () => {
      window.clearTimeout(
        timer
      );
    };
  }, [
    generation,
    refreshWallet,
    setWalletFromGeneration,
  ]);


  // =======================================================
  // PREPARAÇÃO DA FOTO
  // =======================================================

  async function selectFile(
    selectedFile: File
  ) {
    if (
      preparingImage
    ) {
      return;
    }

    setPreparingImage(
      true
    );

    setGenerationError(
      null
    );

    setImagePreparationMessage(
      "Preparando sua foto..."
    );

    try {
      const result =
        await prepareImage(
          selectedFile
        );

      revokePreviewUrl(
        preview
      );

      const preparedFile =
        result.file;

      const objectUrl =
        URL.createObjectURL(
          preparedFile
        );

      setFile(
        preparedFile
      );

      setPreview(
        objectUrl
      );

      setCreatedProductId(
        null
      );

      resetGenerationState();

      if (
        result.wasUpscaled
      ) {
        setImagePreparationMessage(
          "Foto ajustada automaticamente e pronta para usar."
        );

      } else if (
        result.wasResized ||
        result.wasCompressed
      ) {
        setImagePreparationMessage(
          "Foto otimizada automaticamente e pronta para usar."
        );

      } else {
        setImagePreparationMessage(
          "Foto pronta para usar."
        );
      }

      console.log(
        "MARIED STUDIO - FOTO PREPARADA:",
        result
      );

    } catch (error) {
      console.error(
        "Erro ao preparar imagem:",
        error
      );

      setFile(
        null
      );

      setPreview(
        null
      );

      setCreatedProductId(
        null
      );

      resetGenerationState();

      if (
        error instanceof
        ImagePreparationError
      ) {
        setGenerationError(
          error.message
        );

        setImagePreparationMessage(
          null
        );

        return;
      }

      setGenerationError(
        "Não conseguimos preparar essa foto. Tente outra imagem."
      );

      setImagePreparationMessage(
        null
      );

    } finally {
      setPreparingImage(
        false
      );
    }
  }


  // =======================================================
  // INPUT
  // =======================================================

  function handleInputChange(
    event:
      ChangeEvent<HTMLInputElement>
  ) {
    const selectedFile =
      event.target.files?.[0];

    if (
      selectedFile
    ) {
      void selectFile(
        selectedFile
      );
    }
  }


  // =======================================================
  // DROP
  // =======================================================

  function handleDrop(
    event:
      DragEvent<HTMLDivElement>
  ) {
    event.preventDefault();

    setDragging(
      false
    );

    const selectedFile =
      event.dataTransfer
        .files?.[0];

    if (
      selectedFile
    ) {
      void selectFile(
        selectedFile
      );
    }
  }


  // =======================================================
  // REMOVER FOTO
  // =======================================================

  function removeImage() {
    revokePreviewUrl(
      preview
    );

    setPreview(
      null
    );

    setFile(
      null
    );

    setCreatedProductId(
      null
    );

    setImagePreparationMessage(
      null
    );

    resetGenerationState();

    if (
      inputRef.current
    ) {
      inputRef.current.value =
        "";
    }

    if (
      cameraInputRef.current
    ) {
      cameraInputRef.current.value =
        "";
    }
  }


  // =======================================================
  // CATEGORIA
  // =======================================================

  function handleCategoryChange(
    newCategory:
      ProductCategory
  ) {
    setCategory(
      newCategory
    );

    setCreatedProductId(
      null
    );

    setSelectedTemplateId(
      null
    );

    setSceneTemplates(
      []
    );

    setTemplatesError(
      null
    );

    setSelectedModelReferenceId(
      null
    );

    setModelReferences(
      []
    );

    setModelReferencesError(
      null
    );

    resetGenerationState();
  }


  // =======================================================
  // PEÇA EXISTENTE
  // =======================================================

  useEffect(() => {
    let isCurrent =
      true;

    const timer =
      window.setTimeout(
        async () => {
          if (
            !productId
          ) {
            if (
              !isCurrent
            ) {
              return;
            }

            setExistingProduct(
              null
            );

            setExistingProductError(
              null
            );

            setLoadingExistingProduct(
              false
            );

            return;
          }

          setLoadingExistingProduct(
            true
          );

          setExistingProductError(
            null
          );

          setExistingProduct(
            null
          );

          if (
            !isValidUuid(
              productId
            )
          ) {
            setExistingProductError(
              "Peça não encontrada."
            );

            setLoadingExistingProduct(
              false
            );

            return;
          }

          try {
            const product =
              await getProduct(
                productId
              );

            if (
              !isCurrent
            ) {
              return;
            }

            if (
              !product.original_image_url
            ) {
              setExistingProductError(
                "Esta peça não possui uma imagem original disponível."
              );

              setLoadingExistingProduct(
                false
              );

              return;
            }

            setExistingProduct(
              product
            );

            setProductName(
              product.name ||
                "Peça sem nome"
            );

            setCategory(
              product.category as ProductCategory
            );

            setFile(
              null
            );

            setPreview(
              product.original_image_url
            );

            setCreatedProductId(
              product.id
            );

            setGenerationMode(
              null
            );

            setSceneTemplates(
              []
            );

            setSelectedTemplateId(
              null
            );

            setTemplatesError(
              null
            );

            setModelReferences(
              []
            );

            setSelectedModelReferenceId(
              null
            );

            setModelReferencesError(
              null
            );

            setImagePreparationMessage(
              null
            );

            resetGenerationState();

            setStep(
              1
            );

          } catch (error) {
            if (
              !isCurrent
            ) {
              return;
            }

            const message =
              error instanceof ProductsApiError &&
              error.status === 404
                ? "Peça não encontrada."
                : error instanceof Error
                  ? error.message
                  : "Não foi possível carregar esta peça.";

            setExistingProductError(
              message
            );

          } finally {
            if (
              isCurrent
            ) {
              setLoadingExistingProduct(
                false
              );
            }
          }
        },
        0
      );

    return () => {
      isCurrent =
        false;

      window.clearTimeout(
        timer
      );
    };
  }, [productId]);


  // =======================================================
  // CONTINUAR
  // =======================================================

  const canContinue =
    creationSource ===
    "EXISTING_PRODUCT"
      ? Boolean(
          existingProduct &&
          existingProduct.original_image_url &&
          !loadingExistingProduct &&
          !existingProductError
        )
      : Boolean(
          file &&
          category &&
          !preparingImage
        );


  function goToResultStep() {
    if (
      !canContinue
    ) {
      return;
    }

    setGenerationError(
      null
    );

    setStep(
      2
    );
  }


  // =======================================================
  // MODO
  // =======================================================

  function handleModeChange(
    mode:
      GenerationMode
  ) {
    setGenerationMode(
      mode
    );

    setSelectedTemplateId(
      null
    );

    setSceneTemplates(
      []
    );

    setTemplatesError(
      null
    );

    setSelectedModelReferenceId(
      null
    );

    setModelReferences(
      []
    );

    setModelReferencesError(
      null
    );

    resetGenerationState();
  }


  // =======================================================
  // RESULTADO → ESTILO / CONFIRMAÇÃO
  // =======================================================

  async function handleModeContinue() {
    if (
      !generationMode
    ) {
      return;
    }

    if (
      generationMode ===
      "STILL"
    ) {
      setSelectedTemplateId(
        null
      );

      setSelectedModelReferenceId(
        null
      );

      setSceneTemplates(
        []
      );

      setModelReferences(
        []
      );

      setTemplatesError(
        null
      );

      setModelReferencesError(
        null
      );

      setStep(
        4
      );

      return;
    }

    setStep(
      3
    );

    setLoadingTemplates(
      modeUsesSceneTemplate(
        generationMode
      )
    );

    setTemplatesError(
      null
    );

    setSelectedTemplateId(
      null
    );

    setSelectedModelReferenceId(
      null
    );

    setLoadingModelReferences(
      modeUsesModelReference(
        generationMode
      )
    );

    setModelReferencesError(
      null
    );

    try {
      if (
        modeUsesSceneTemplate(
          generationMode
        )
      ) {
        const templates =
          await getSceneTemplates({
            category,
            mode:
              generationMode,
          });

        setSceneTemplates(
          templates
        );

        setModelReferences(
          []
        );

        if (
          templates.length ===
          1
        ) {
          setSelectedTemplateId(
            templates[0].id
          );
        }
      }

      if (
        modeUsesModelReference(
          generationMode
        )
      ) {
        const references =
          await getModelReferences();

        setModelReferences(
          references
        );

        setSceneTemplates(
          []
        );

        if (
          references.length ===
          1
        ) {
          setSelectedModelReferenceId(
            references[0].id
          );
        }
      }

    } catch (error) {
      console.error(
        "Erro ao carregar opções visuais:",
        error
      );

      setSceneTemplates(
        []
      );

      setModelReferences(
        []
      );

      const message =
        error instanceof Error
          ? error.message
          : "Não foi possível carregar as opções.";

      if (
        modeUsesSceneTemplate(
          generationMode
        )
      ) {
        setTemplatesError(
          message
        );
      }

      if (
        modeUsesModelReference(
          generationMode
        )
      ) {
        setModelReferencesError(
          message
        );
      }

    } finally {
      setLoadingTemplates(
        false
      );

      setLoadingModelReferences(
        false
      );
    }
  }


  // =======================================================
  // VOLTAR DA CONFIRMAÇÃO
  // =======================================================

  function handleBackFromConfirmation() {
    if (
      isGenerating
    ) {
      return;
    }

    setGenerationError(
      null
    );

    if (
      generationMode ===
      "STILL"
    ) {
      setStep(
        2
      );

      return;
    }

    setStep(
      3
    );
  }


  // =======================================================
  // GERAÇÃO REAL
  // =======================================================

  async function handleGenerate() {
    if (
      isGenerating
    ) {
      return;
    }

    if (
      generation &&
      isPendingGeneration(
        generation
      )
    ) {
      setGenerationError(
        "Já existe uma criação em andamento. Aguarde ela ficar pronta antes de iniciar uma nova."
      );

      setStep(
        5
      );

      return;
    }

    if (
      !canOperateStudio
    ) {
      setGenerationError(
        accessMessage
      );

      router.replace(
        "/assinatura"
      );

      return;
    }

    if (
      creationSource ===
        "NEW_PRODUCT" &&
      !file
    ) {
      setGenerationError(
        "A imagem original da peça não foi encontrada."
      );

      return;
    }

    if (
      creationSource ===
        "EXISTING_PRODUCT" &&
      (
        !existingProduct ||
        !existingProduct.original_image_url
      )
    ) {
      setGenerationError(
        "Esta peça não possui uma imagem original disponível."
      );

      return;
    }

    if (
      !generationMode
    ) {
      setGenerationError(
        "Selecione o tipo de resultado."
      );

      return;
    }

    if (
      modeUsesSceneTemplate(
        generationMode
      ) &&
      !selectedTemplateId
    ) {
      setGenerationError(
        "Selecione um cenário antes de continuar."
      );

      return;
    }

    if (
      modeUsesModelReference(
        generationMode
      ) &&
      !selectedModelReferenceId
    ) {
      setGenerationError(
        "Selecione uma modelo antes de continuar."
      );

      return;
    }


    // =====================================================
    // PROTEÇÃO ADICIONAL DE SALDO
    // =====================================================

    if (
      availableCredits !== null &&
      availableCredits < 1
    ) {
      setGenerationError(
        "Você não possui créditos disponíveis para esta geração."
      );

      return;
    }


    setIsGenerating(
      true
    );

    setGenerationError(
      null
    );

    generationPollAttempts.current =
      0;

    try {
      // ===================================================
      // 1. PRODUTO
      // ===================================================

      let productIdToGenerate =
        creationSource ===
        "EXISTING_PRODUCT"
          ? existingProduct?.id ?? null
          : createdProductId;

      if (
        !productIdToGenerate
      ) {
        if (
          !file
        ) {
          setGenerationError(
            "A imagem original da peça não foi encontrada."
          );

          return;
        }

        const product =
          await createProduct({
            name:
              productName.trim() ||
              "Peça sem nome",

            category,

            file,
          });

        productIdToGenerate =
          product.id;

        setCreatedProductId(
          product.id
        );

        console.log(
          "PRODUTO CRIADO COM SUCESSO:",
          product
        );

        console.log(
          "PRODUCT ID:",
          product.id
        );

      } else {
        console.log(
          "Produto já existente:",
          productIdToGenerate
        );
      }


      // ===================================================
      // 2. IDEMPOTENCY KEY
      // ===================================================

      let key =
        idempotencyKey;

      if (
        !key
      ) {
        key =
          createIdempotencyKey();

        setIdempotencyKey(
          key
        );
      }


      // ===================================================
      // 3. GERAÇÃO
      // ===================================================

      console.log(
        "CRIANDO GERAÇÃO:",
        {
          productId:
            productIdToGenerate,
          generationMode,
          selectedTemplateId,
          selectedModelReferenceId,
          idempotencyKey:
            key,
        }
      );


      const createdGeneration =
        await createGeneration({
          productId:
            productIdToGenerate,

          mode:
            generationMode,

          sceneTemplateId:
            modeUsesSceneTemplate(
              generationMode
            )
              ? selectedTemplateId
              : null,

          modelReferenceId:
            modeUsesModelReference(
              generationMode
            )
              ? selectedModelReferenceId
              : null,

          idempotencyKey:
            key,
        });


      setGeneration(
        createdGeneration
      );


      console.log(
        "GERAÇÃO RECEBIDA:",
        createdGeneration
      );


      // ===================================================
      // FAILED
      // ===================================================

      if (
        createdGeneration.status ===
        "FAILED"
      ) {
        // O backend pode ter devolvido
        // uma reserva de crédito.
        await refreshWallet();

        setGenerationError(
          createdGeneration.error_message ||
          "A geração não foi concluída. Tente novamente."
        );

        return;
      }


      // ===================================================
      // COMPLETED
      // ===================================================

      if (
        createdGeneration.status ===
          "COMPLETED" &&
        createdGeneration.image_url
      ) {
        // Atualização imediata usando
        // o valor já retornado pela Generation.

        setWalletFromGeneration(
          createdGeneration.available_credits
        );


        // Depois buscamos novamente a carteira
        // real no Django para garantir consistência.

        await refreshWallet();


        setStep(
          5
        );

        return;
      }


      // ===================================================
      // PROCESSANDO
      // ===================================================

      if (
        isPendingGeneration(
          createdGeneration
        )
      ) {
        // Já pode existir reserva ativa,
        // então sincronizamos o saldo.

        await refreshWallet();


        setStep(
          5
        );

        return;
      }


      await refreshWallet();


      setGenerationError(
        "A geração foi criada, mas ainda não recebemos a imagem final."
      );

    } catch (error) {
      console.error(
        "Erro durante a geração:",
        error
      );


      // Se a requisição falhar, consultamos
      // novamente o backend porque ele pode
      // ter reservado ou devolvido crédito.

      try {
        await refreshWallet();
      } catch {
        // Mantemos o erro principal abaixo.
      }

      if (
        error instanceof ApiError &&
        error.status === 409
      ) {
        try {
          const activeGeneration =
            await getActiveGeneration();

          if (
            activeGeneration
          ) {
            setGeneration(
              activeGeneration
            );

            setGenerationError(
              null
            );

            setStep(
              5
            );

            return;
          }
        } catch {
          // Mantemos a mensagem original do 409.
        }
      }


      setGenerationError(
        error instanceof Error
          ? error.message
          : "Não foi possível gerar sua imagem."
      );

    } finally {
      setIsGenerating(
        false
      );
    }
  }


  // =======================================================
  // NOVA CRIAÇÃO
  // =======================================================

  function handleNewCreation() {
    revokePreviewUrl(
      preview
    );

    setStep(
      1
    );

    setProductName(
      ""
    );

    setCategory(
      "EARRING"
    );

    setFile(
      null
    );

    setPreview(
      null
    );

    setGenerationMode(
      null
    );

    setSceneTemplates(
      []
    );

    setSelectedTemplateId(
      null
    );

    setModelReferences(
      []
    );

    setSelectedModelReferenceId(
      null
    );

    setModelReferencesError(
      null
    );

    setTemplatesError(
      null
    );

    setImagePreparationMessage(
      null
    );

    setCreatedProductId(
      null
    );

    setGeneration(
      null
    );

    setGenerationError(
      null
    );

    setIdempotencyKey(
      null
    );

    setExistingProduct(
      null
    );

    setExistingProductError(
      null
    );

    setLoadingExistingProduct(
      false
    );

    if (
      inputRef.current
    ) {
      inputRef.current.value =
        "";
    }

    if (
      cameraInputRef.current
    ) {
      cameraInputRef.current.value =
        "";
    }

    if (
      creationSource ===
      "EXISTING_PRODUCT"
    ) {
      router.push(
        "/criar"
      );
    }
  }


  // =======================================================
  // NOVA GERAÇÃO DA MESMA PEÇA
  // =======================================================

  function handleAnotherGeneration() {
    if (
      generation &&
      isPendingGeneration(
        generation
      )
    ) {
      setGenerationError(
        "Aguarde a criação em andamento ficar pronta antes de iniciar uma nova."
      );

      setStep(
        5
      );

      return;
    }

    setGeneration(
      null
    );

    setGenerationError(
      null
    );

    setIdempotencyKey(
      null
    );

    setSelectedTemplateId(
      null
    );

    setSelectedModelReferenceId(
      null
    );

    setSceneTemplates(
      []
    );

    setModelReferences(
      []
    );

    setModelReferencesError(
      null
    );

    setGenerationMode(
      null
    );

    setStep(
      2
    );
  }


  // =======================================================
  // PROGRESSO
  // =======================================================

  const progress =
    step >= 4
      ? "100%"
      : `${step * 25}%`;


  const hasActiveGeneration =
    generation
      ? isPendingGeneration(
          generation
        )
      : false;


  const pendingGenerationCopy =
    generation
      ? getPendingGenerationCopy(
          generation
        )
      : null;


  const selectionTitle =
    modeUsesModelReference(
      generationMode
    )
      ? "Escolha a modelo."
      : "Escolha o cenário.";


  const selectionDescription =
    modeUsesModelReference(
      generationMode
    )
      ? "Selecione a referência visual que será usada nesta criação."
      : "Selecione o cenário comercial para apresentar a sua peça.";


  const selectionEmptyTitle =
    modeUsesModelReference(
      generationMode
    )
      ? "Nenhuma modelo disponível"
      : "Nenhum cenário disponível";


  const selectionEmptyDescription =
    modeUsesModelReference(
      generationMode
    )
      ? "Não existem modelos ativos para seleção no momento."
      : "Não existem cenários ativos para esta categoria no momento.";


  const selectionOptions =
    modeUsesModelReference(
      generationMode
    )
      ? modelReferences.map(
          (
            modelReference
          ) => ({
            id:
              modelReference.id,
            name:
              modelReference.name,
            description:
              modelReference.description,
            previewImageUrl:
              modelReference.preview_image_url,
          })
        )
      : sceneTemplates.map(
          (
            template
          ) => ({
            id:
              template.id,
            name:
              template.name,
            description:
              `Cenário ${template.name} para esta composição.`,
            previewImageUrl:
              template.preview_image,
          })
        );


  const selectedVisualName =
    selectedModelReference?.name ??
    selectedTemplate?.name ??
    null;


  const selectedVisualLabel =
    modeUsesModelReference(
      generationMode
    )
      ? "Modelo"
      : "Cenário";


  const modeLabel =
    generationMode ===
    "STILL"
      ? "Still"
      : generationMode ===
        "BODY_DETAIL"
        ? "Detalhe no Corpo"
        : generationMode ===
          "MODEL"
          ? "Na Modelo"
          : generationMode ===
            "INSTAGRAM"
            ? "Instagramável"
            : "-";


  // =======================================================
  // RENDER
  // =======================================================

  if (
    loadingBillingAccess
  ) {
    return (
      <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mx-auto flex min-h-[420px] max-w-[900px] items-center justify-center">
          <div className="flex items-center gap-3 text-sm text-[var(--maried-cocoa)]">
            <LoaderCircle
              size={
                18
              }
              className="animate-spin text-[var(--maried-gold)]"
            />
            Verificando assinatura...
          </div>
        </div>
      </main>
    );
  }


  if (
    !canOperateStudio
  ) {
    return (
      <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mx-auto flex min-h-[420px] max-w-[900px] items-center justify-center">
          <section className="maried-card max-w-md p-6 text-center">
            <Sparkles
              size={
                28
              }
              className="mx-auto text-[var(--maried-gold)]"
            />

            <h1 className="mt-4 text-lg font-semibold text-[var(--maried-espresso)]">
              Assinatura necessária
            </h1>

            <p className="mt-2 text-sm leading-6 text-[var(--maried-cocoa)]">
              {accessMessage}
            </p>

            <Link
              href="/assinatura"
              className="mt-5 inline-flex h-11 items-center justify-center rounded-xl bg-[var(--maried-gold)] px-5 text-sm font-medium text-white"
            >
              {accessCtaLabel}
            </Link>
          </section>
        </div>
      </main>
    );
  }


  return (
    <main className="px-4 py-6 sm:px-6 lg:px-8 lg:py-8">

      <div className="mx-auto max-w-[900px]">

        {/* =================================================
            PROGRESSO
        ================================================= */}

        {step !== 5 ? (

          <div className="mb-8">

            <div className="flex items-center justify-between gap-3 text-[11px] font-medium uppercase tracking-[0.15em] text-[var(--maried-cocoa)]">

              {stepLabels.map(
                (item) => {

                  const active =
                    step ===
                    item.step;

                  const completed =
                    step >
                    item.step;

                  return (
                    <span
                      key={
                        item.step
                      }

                      className={[
                        item.step > 2
                          ? "hidden sm:inline"
                          : "",

                        active
                          ? "text-[var(--maried-gold)]"
                          : "",

                        completed
                          ? "text-[var(--maried-coffee)]"
                          : "",
                      ].join(" ")}
                    >

                      {String(
                        item.step
                      ).padStart(
                        2,
                        "0"
                      )}{" "}

                      {
                        item.label
                      }

                    </span>
                  );
                }
              )}

            </div>


            <div className="mt-3 h-[2px] overflow-hidden rounded-full bg-[var(--maried-sand)]">

              <motion.div
                animate={{
                  width:
                    progress,
                }}

                transition={{
                  duration:
                    0.35,

                  ease:
                    "easeOut",
                }}

                className="h-full rounded-full bg-[var(--maried-gold)]"
              />

            </div>

          </div>

        ) : null}


        <AnimatePresence
          mode="wait"
        >

          {/* =================================================
              ETAPA 01
          ================================================= */}

          {step === 1 &&
          creationSource ===
            "EXISTING_PRODUCT" ? (

            <ExistingProductStep
              key="step-1-existing"
              product={
                existingProduct
              }
              loading={
                loadingExistingProduct
              }
              error={
                existingProductError
              }
              onContinue={
                goToResultStep
              }
            />

          ) : null}


          {step === 1 &&
          creationSource ===
            "NEW_PRODUCT" ? (

            <motion.div
              key="step-1"

              initial={{
                opacity:
                  0,

                x:
                  -12,
              }}

              animate={{
                opacity:
                  1,

                x:
                  0,
              }}

              exit={{
                opacity:
                  0,

                x:
                  -18,
              }}

              transition={{
                duration:
                  0.28,
              }}
            >

              <motion.section
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
                  duration:
                    0.35,
                }}
              >

                <h1 className="text-[30px] font-semibold leading-tight tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[38px]">
                  Vamos começar pela sua peça.
                </h1>


                <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--maried-cocoa)]">
                  Tire uma foto ou escolha uma imagem.
                  O MARIED STUDIO prepara a qualidade
                  automaticamente para você.
                </p>

              </motion.section>


              <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">

                {/* FOTO */}

                <motion.section
                  initial={{
                    opacity:
                      0,

                    y:
                      12,
                  }}

                  animate={{
                    opacity:
                      1,

                    y:
                      0,
                  }}

                  transition={{
                    duration:
                      0.35,

                    delay:
                      0.05,
                  }}

                  className="maried-card p-4 sm:p-5"
                >

                  <input
                    ref={
                      inputRef
                    }

                    type="file"

                    accept="image/jpeg,image/png,image/webp"

                    className="hidden"

                    onChange={
                      handleInputChange
                    }
                  />


                  <input
                    ref={
                      cameraInputRef
                    }

                    type="file"

                    accept="image/*"

                    capture="environment"

                    className="hidden"

                    onChange={
                      handleInputChange
                    }
                  />


                  <AnimatePresence
                    mode="wait"
                  >

                    {!preview ? (

                      <motion.div
                        key="upload"

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

                          scale:
                            0.98,
                        }}

                        onDragOver={(
                          event
                        ) => {
                          event.preventDefault();

                          setDragging(
                            true
                          );
                        }}

                        onDragLeave={() => {
                          setDragging(
                            false
                          );
                        }}

                        onDrop={
                          handleDrop
                        }

                        onClick={() => {
                          if (
                            !preparingImage
                          ) {
                            inputRef.current?.click();
                          }
                        }}

                        className={[
                          "flex min-h-[330px] cursor-pointer flex-col items-center justify-center rounded-[18px] border border-dashed px-6 text-center transition-all",

                          preparingImage
                            ? "pointer-events-none opacity-60"
                            : "",

                          dragging
                            ? "border-[var(--maried-gold)] bg-[var(--maried-soft-gold)]"
                            : "border-[var(--maried-champagne)] bg-[rgba(250,248,239,0.45)] hover:border-[var(--maried-gold)]",
                        ].join(" ")}
                      >

                        <motion.div
                          animate={
                            dragging
                              ? {
                                  y:
                                    -4,

                                  scale:
                                    1.04,
                                }
                              : {
                                  y:
                                    0,

                                  scale:
                                    1,
                                }
                          }

                          className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--maried-soft-gold)]"
                        >

                          <UploadCloud
                            size={
                              25
                            }

                            strokeWidth={
                              1.5
                            }

                            className="text-[var(--maried-gold)]"
                          />

                        </motion.div>


                        <h2 className="mt-5 text-base font-semibold">
                          Adicione sua foto
                        </h2>


                        <p className="mt-2 max-w-[280px] text-xs leading-5 text-[var(--maried-cocoa)]">
                          No computador, arraste a imagem
                          ou clique para selecionar.
                        </p>


                        <span className="mt-5 text-[10px] uppercase tracking-[0.12em] text-[var(--maried-caramel)]">
                          JPG, PNG ou WEBP • preparação automática
                        </span>

                      </motion.div>

                    ) : (

                      <motion.div
                        key="preview"

                        initial={{
                          opacity:
                            0,

                          scale:
                            0.98,
                        }}

                        animate={{
                          opacity:
                            1,

                          scale:
                            1,
                        }}

                        exit={{
                          opacity:
                            0,
                        }}

                        className="relative overflow-hidden rounded-[18px] bg-[var(--maried-cream)]"
                      >

                        <div className="relative aspect-square">

                          <Image
                            src={
                              preview
                            }

                            alt="Prévia da peça"

                            fill

                            unoptimized

                            className="object-contain p-5"
                          />

                        </div>


                        <button
                          type="button"

                          onClick={
                            removeImage
                          }

                          disabled={
                            preparingImage
                          }

                          className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full border border-[var(--maried-sand)] bg-white/90 text-[var(--maried-coffee)] shadow-sm backdrop-blur disabled:opacity-50"
                        >

                          <X
                            size={
                              17
                            }
                          />

                        </button>


                        <div className="border-t border-[var(--maried-sand)] bg-white px-4 py-3">

                          <div className="flex items-center gap-2">

                            <Check
                              size={
                                15
                              }

                              className="text-[var(--status-success)]"
                            />


                            <span className="truncate text-xs font-medium">
                              {
                                file?.name
                              }
                            </span>

                          </div>

                        </div>

                      </motion.div>

                    )}

                  </AnimatePresence>


                  {/* MOBILE */}

                  <div className="mt-4 grid grid-cols-2 gap-3 sm:hidden">

                    <button
                      type="button"

                      disabled={
                        preparingImage
                      }

                      onClick={() => {
                        cameraInputRef.current?.click();
                      }}

                      className="flex h-11 items-center justify-center gap-2 rounded-xl bg-[var(--maried-coffee)] px-3 text-xs font-medium text-white"
                    >

                      <Camera
                        size={
                          16
                        }
                      />

                      Tirar foto

                    </button>


                    <button
                      type="button"

                      disabled={
                        preparingImage
                      }

                      onClick={() => {
                        inputRef.current?.click();
                      }}

                      className="flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white px-3 text-xs font-medium text-[var(--maried-coffee)]"
                    >

                      <ImagePlus
                        size={
                          16
                        }
                      />

                      Galeria

                    </button>

                  </div>


                  {/* PREPARAÇÃO */}

                  {preparingImage ? (

                    <div className="mt-3 flex items-center gap-3 rounded-xl bg-[var(--maried-soft-gold)] px-4 py-3 text-xs text-[var(--maried-coffee)]">

                      <LoaderCircle
                        size={
                          16
                        }

                        className="animate-spin"
                      />

                      Preparando sua foto...

                    </div>

                  ) : null}


                  {!preparingImage &&
                  imagePreparationMessage ? (

                    <div className="mt-3 flex items-center gap-2 rounded-xl bg-green-50 px-4 py-3 text-xs text-green-700">

                      <Check
                        size={
                          15
                        }
                      />

                      {
                        imagePreparationMessage
                      }

                    </div>

                  ) : null}


                  {generationError &&
                  step === 1 ? (

                    <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">

                      {
                        generationError
                      }

                    </div>

                  ) : null}

                </motion.section>


                {/* DADOS */}

                <motion.section
                  initial={{
                    opacity:
                      0,

                    y:
                      12,
                  }}

                  animate={{
                    opacity:
                      1,

                    y:
                      0,
                  }}

                  transition={{
                    duration:
                      0.35,

                    delay:
                      0.1,
                  }}

                  className="space-y-6"
                >

                  <div className="maried-card p-5">

                    <label
                      htmlFor="product-name"

                      className="text-xs font-medium text-[var(--maried-coffee)]"
                    >
                      Nome da peça
                    </label>


                    <p className="mt-1 text-[11px] text-[var(--maried-caramel)]">
                      Opcional
                    </p>


                    <input
                      id="product-name"

                      value={
                        productName
                      }

                      onChange={(
                        event
                      ) => {
                        setProductName(
                          event.target.value
                        );

                        setCreatedProductId(
                          null
                        );

                        resetGenerationState();
                      }}

                      placeholder="Ex.: Brinco Floral Dourado"

                      className="mt-3 h-12 w-full rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm outline-none focus:border-[var(--maried-gold)]"
                    />

                  </div>


                  <div className="maried-card p-5">

                    <h2 className="text-xs font-medium text-[var(--maried-coffee)]">
                      Categoria
                    </h2>


                    <p className="mt-1 text-[11px] text-[var(--maried-caramel)]">
                      Selecione o tipo da joia.
                    </p>


                    <div className="mt-4 grid grid-cols-2 gap-2">

                      {categories.map(
                        (
                          item
                        ) => {

                          const selected =
                            category ===
                            item.value;

                          return (
                            <button
                              key={
                                item.value
                              }

                              type="button"

                              onClick={() => {
                                handleCategoryChange(
                                  item.value
                                );
                              }}

                              className={[
                                "relative min-h-[48px] rounded-xl border px-3 text-xs",

                                selected
                                  ? "border-[var(--maried-gold)] bg-[var(--maried-soft-gold)]"
                                  : "border-[var(--maried-sand)] bg-white",
                              ].join(" ")}
                            >

                              {
                                item.label
                              }


                              {selected ? (

                                <Check
                                  size={
                                    12
                                  }

                                  className="absolute right-2 top-2 text-[var(--maried-gold)]"
                                />

                              ) : null}

                            </button>
                          );
                        }
                      )}

                    </div>

                  </div>


                  <motion.button
                    type="button"

                    disabled={
                      !canContinue
                    }

                    whileTap={
                      canContinue
                        ? {
                            scale:
                              0.985,
                          }
                        : undefined
                    }

                    onClick={
                      goToResultStep
                    }

                    className={[
                      "flex h-[52px] w-full items-center justify-center gap-2 rounded-xl",

                      canContinue
                        ? "bg-[var(--maried-gold)] text-white"
                        : "cursor-not-allowed bg-[var(--maried-sand)] text-[var(--maried-caramel)]",
                    ].join(" ")}
                  >

                    Continuar

                    <ArrowRight
                      size={
                        17
                      }
                    />

                  </motion.button>

                </motion.section>

              </div>

            </motion.div>

          ) : null}


          {/* =================================================
              ETAPA 02
          ================================================= */}

          {step === 2 ? (

            <ResultModeStep
              key="step-2"

              value={
                generationMode
              }

              onChange={
                handleModeChange
              }

              onBack={() => {
                setStep(
                  1
                );
              }}

              onContinue={
                handleModeContinue
              }
            />

          ) : null}


          {/* =================================================
              ETAPA 03
          ================================================= */}

          {step === 3 ? (

            <StyleStep
              key="step-3"

              title={
                selectionTitle
              }

              description={
                selectionDescription
              }

              emptyTitle={
                selectionEmptyTitle
              }

              emptyDescription={
                selectionEmptyDescription
              }

              eyebrow={
                selectedVisualLabel
              }

              options={
                selectionOptions
              }

              selectedOptionId={
                modeUsesModelReference(
                  generationMode
                )
                  ? selectedModelReferenceId
                  : selectedTemplateId
              }

              loading={
                loadingTemplates ||
                loadingModelReferences
              }

              error={
                templatesError ??
                modelReferencesError
              }

              onChange={(optionId) => {
                if (
                  modeUsesModelReference(
                    generationMode
                  )
                ) {
                  setSelectedModelReferenceId(
                    optionId
                  );

                  return;
                }

                setSelectedTemplateId(
                  optionId
                );
              }}

              onBack={() => {
                setStep(
                  2
                );
              }}

              onContinue={() => {
                resetGenerationState();

                setStep(
                  4
                );
              }}
            />

          ) : null}


          {/* =================================================
              ETAPA 04
          ================================================= */}

          {step === 4 ? (

            <ConfirmationStep
              key="step-4"

              preview={
                preview
              }

              productName={
                productName
              }

              category={
                category
              }

              mode={
                generationMode
              }

              selectionLabel={
                selectedVisualLabel
              }

              selectionName={
                selectedVisualName
              }

              isGenerating={
                isGenerating ||
                loadingActiveGeneration ||
                hasActiveGeneration
              }

              error={
                generationError
              }

              onBack={
                handleBackFromConfirmation
              }

              onGenerate={
                handleGenerate
              }
            />

          ) : null}


          {/* =================================================
              ETAPA 05
              ACOMPANHAMENTO
          ================================================= */}

          {step === 5 &&
          generation &&
          !generation.image_url ? (

            <motion.section
              key="step-5-processing"

              initial={{
                opacity:
                  0,

                y:
                  14,
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
              }}

              className="mx-auto max-w-2xl text-center"
            >

              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--maried-soft-gold)]">
                {isPendingGeneration(
                  generation
                ) ? (
                  <LoaderCircle
                    size={22}
                    className="animate-spin text-[var(--maried-gold)]"
                  />
                ) : (
                  <X
                    size={22}
                    className="text-red-500"
                  />
                )}
              </div>

              <h1 className="mt-5 text-[30px] font-semibold text-[var(--maried-espresso)] sm:text-[38px]">
                {pendingGenerationCopy?.title}
              </h1>

              <p className="mt-3 text-sm leading-6 text-[var(--maried-cocoa)]">
                {generationError ||
                  pendingGenerationCopy?.description}
              </p>

              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <Link
                  href="/criacoes"
                  className="flex h-12 items-center justify-center rounded-xl bg-[var(--maried-gold)] text-sm font-medium text-white"
                >
                  Minhas criações
                </Link>

                {!hasActiveGeneration ? (
                  <button
                    type="button"
                    onClick={
                      handleAnotherGeneration
                    }
                    className="flex h-12 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white text-sm font-medium text-[var(--maried-coffee)]"
                  >
                    Criar outra versão
                  </button>
                ) : null}
              </div>

            </motion.section>

          ) : null}


          {/* =================================================
              ETAPA 05
              RESULTADO FINAL
          ================================================= */}

          {step === 5 &&
          generation?.image_url ? (

            <motion.section
              key="step-5"

              initial={{
                opacity:
                  0,

                y:
                  14,
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
              }}
            >

              <div className="text-center">

                <motion.div
                  initial={{
                    scale:
                      0.8,
                  }}

                  animate={{
                    scale:
                      1,
                  }}

                  className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[var(--maried-soft-gold)]"
                >

                  <Sparkles
                    size={
                      22
                    }

                    className="text-[var(--maried-gold)]"
                  />

                </motion.div>


                <h1 className="mt-5 text-[30px] font-semibold text-[var(--maried-espresso)] sm:text-[38px]">
                  Sua imagem está pronta.
                </h1>


                <p className="mt-2 text-sm text-[var(--maried-cocoa)]">
                  A criação foi processada
                  pelo MARIED STUDIO.
                </p>

              </div>


              <div className="mt-8 grid gap-5 lg:grid-cols-[1fr_320px]">

                {/* IMAGEM */}

                <div className="maried-card overflow-hidden p-4">

                  <div className="relative aspect-square overflow-hidden rounded-[18px] bg-[var(--maried-cream)]">

                    <Image
                      src={
                        generation.image_url
                      }

                      alt="Imagem gerada pelo MARIED STUDIO"

                      fill

                      unoptimized

                      className="object-contain"
                    />

                  </div>

                </div>


                {/* AÇÕES */}

                <div className="space-y-4">

                  <div className="maried-card p-5">

                    <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--maried-caramel)]">
                      Resultado
                    </div>


                    <div className="mt-2 text-sm font-semibold">
                      {
                        modeLabel
                      }
                    </div>


                    {selectedVisualName ? (

                      <>
                        <div className="mt-5 text-[10px] uppercase tracking-[0.14em] text-[var(--maried-caramel)]">
                          {
                            selectedVisualLabel
                          }
                        </div>


                        <div className="mt-2 text-sm font-semibold">
                          {
                            selectedVisualName
                          }
                        </div>
                      </>

                    ) : null}


                    <div className="mt-5 text-[10px] uppercase tracking-[0.14em] text-[var(--maried-caramel)]">
                      Créditos disponíveis
                    </div>


                    <div className="mt-2 text-2xl font-semibold">
                      {
                        availableCredits ??
                        generation.available_credits
                      }
                    </div>

                  </div>


                  <a
                    href={
                      generation.image_url
                    }

                    target="_blank"

                    rel="noreferrer"

                    className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] text-sm font-medium text-white"
                  >

                    <Download
                      size={
                        17
                      }
                    />

                    Abrir imagem

                  </a>


                  <button
                    type="button"

                    onClick={
                      handleAnotherGeneration
                    }

                    className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white text-sm font-medium text-[var(--maried-coffee)]"
                  >

                    <RotateCcw
                      size={
                        17
                      }
                    />

                    Criar outra versão

                  </button>


                  <button
                    type="button"

                    onClick={
                      handleNewCreation
                    }

                    className="flex h-12 w-full items-center justify-center gap-2 rounded-xl border border-[var(--maried-sand)] bg-white text-sm font-medium text-[var(--maried-coffee)]"
                  >

                    <Plus
                      size={
                        17
                      }
                    />

                    Nova peça

                  </button>

                </div>

              </div>

            </motion.section>

          ) : null}

        </AnimatePresence>

      </div>

    </main>
  );
}


type ExistingProductStepProps = {
  product:
    ExistingProduct | null;

  loading:
    boolean;

  error:
    string | null;

  onContinue:
    () => void;
};


function ExistingProductStep({
  product,
  loading,
  error,
  onContinue,
}: ExistingProductStepProps) {
  return (
    <motion.section
      key="step-1-existing"
      initial={{
        opacity:
          0,

        x:
          -12,
      }}
      animate={{
        opacity:
          1,

        x:
          0,
      }}
      exit={{
        opacity:
          0,

        x:
          -18,
      }}
      transition={{
        duration:
          0.28,
      }}
      className="space-y-6"
    >

      <div>

        <h1 className="text-[30px] font-semibold leading-tight tracking-[-0.035em] text-[var(--maried-espresso)] sm:text-[38px]">
          Criar nova imagem.
        </h1>


        <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--maried-cocoa)]">
          Usaremos a peça selecionada como base
          para a próxima criação.
        </p>

      </div>


      {loading ? (

        <div className="maried-card flex min-h-[260px] items-center justify-center p-6">

          <div className="flex items-center gap-3 text-sm text-[var(--maried-cocoa)]">

            <LoaderCircle
              size={
                18
              }
              className="animate-spin text-[var(--maried-gold)]"
            />

            Carregando peça...

          </div>

        </div>

      ) : null}


      {!loading &&
      error ? (

        <div className="maried-card p-6">

          <div className="text-sm font-semibold text-[var(--maried-espresso)]">
            Não foi possível carregar esta peça.
          </div>


          <p className="mt-2 text-sm leading-6 text-[var(--maried-cocoa)]">
            {
              error
            }
          </p>


          <Link
            href="/pecas"
            className="mt-5 inline-flex h-11 items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white px-4 text-sm font-medium text-[var(--maried-coffee)]"
          >
            Voltar para minhas peças
          </Link>

        </div>

      ) : null}


      {!loading &&
      !error &&
      product ? (

        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">

          <div className="maried-card overflow-hidden p-4">

            <div className="relative aspect-square overflow-hidden rounded-[18px] bg-[var(--maried-cream)]">

              {product.original_image_url ? (

                <Image
                  src={
                    product.original_image_url
                  }
                  alt={
                    product.name ||
                    "Peça selecionada"
                  }
                  fill
                  unoptimized
                  className="object-contain p-5"
                />

              ) : (

                <div className="flex h-full items-center justify-center">

                  <ImagePlus
                    size={
                      40
                    }
                    className="text-[var(--maried-gold)]"
                  />

                </div>

              )}

            </div>

          </div>


          <div className="space-y-4">

            <div className="maried-card p-5">

              <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--maried-caramel)]">
                Peça selecionada
              </div>


              <div className="mt-2 text-lg font-semibold text-[var(--maried-espresso)]">
                {
                  product.name ||
                  "Peça sem nome"
                }
              </div>


              <div className="mt-5 text-[10px] uppercase tracking-[0.14em] text-[var(--maried-caramel)]">
                Categoria
              </div>


              <div className="mt-2 text-sm font-medium text-[var(--maried-coffee)]">
                {
                  product.category_label ||
                  getCategoryLabel(
                    product.category
                  )
                }
              </div>


              <p className="mt-5 text-sm leading-6 text-[var(--maried-cocoa)]">
                Esta peça será reutilizada.
                Nenhum novo produto será criado
                nesta etapa.
              </p>

            </div>


            <button
              type="button"
              onClick={
                onContinue
              }
              className="flex h-[52px] w-full items-center justify-center gap-2 rounded-xl bg-[var(--maried-gold)] text-sm font-medium text-white"
            >
              Continuar

              <ArrowRight
                size={
                  17
                }
              />
            </button>


            <Link
              href="/pecas"
              className="flex h-12 w-full items-center justify-center rounded-xl border border-[var(--maried-sand)] bg-white text-sm font-medium text-[var(--maried-coffee)]"
            >
              Voltar para minhas peças
            </Link>

          </div>

        </div>

      ) : null}

    </motion.section>
  );
}
