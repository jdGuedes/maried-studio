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
  createGeneration,
  createProduct,
  getModelReferences,
  getSceneTemplates,
} from "@/lib/api";

import {
  ImagePreparationError,
  prepareImage,
} from "@/lib/image-preparation";

import {
  useCreditWallet,
} from "@/providers/credit-wallet-provider";

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


// =========================================================
// WIZARD
// =========================================================

type WizardStep =
  | 1
  | 2
  | 3
  | 4
  | 5;


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

export function CreationWizard() {
  const inputRef =
    useRef<HTMLInputElement>(
      null
    );

  const cameraInputRef =
    useRef<HTMLInputElement>(
      null
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
      if (preview) {
        URL.revokeObjectURL(
          preview
        );
      }
    };
  }, [preview]);


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
  }


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

      if (
        preview
      ) {
        URL.revokeObjectURL(
          preview
        );
      }

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
    if (
      preview
    ) {
      URL.revokeObjectURL(
        preview
      );
    }

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
  // CONTINUAR
  // =======================================================

  const canContinue =
    Boolean(
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
      !file
    ) {
      setGenerationError(
        "A imagem original da peça não foi encontrada."
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

    try {
      // ===================================================
      // 1. PRODUTO
      // ===================================================

      let productId =
        createdProductId;

      if (
        !productId
      ) {
        const product =
          await createProduct({
            name:
              productName.trim() ||
              "Peça sem nome",

            category,

            file,
          });

        productId =
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
          productId
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
          productId,
          generationMode,
          selectedTemplateId,
          selectedModelReferenceId,
          idempotencyKey:
            key,
        }
      );


      const createdGeneration =
        await createGeneration({
          productId,

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
        createdGeneration.status ===
          "PROCESSING" ||
        createdGeneration.status ===
          "CREATED" ||
        createdGeneration.status ===
          "CREDIT_RESERVED"
      ) {
        // Já pode existir reserva ativa,
        // então sincronizamos o saldo.

        await refreshWallet();


        setGenerationError(
          "Sua imagem entrou em processamento. Em breve vamos acompanhar esse status automaticamente."
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
    if (
      preview
    ) {
      URL.revokeObjectURL(
        preview
      );
    }

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
  // NOVA GERAÇÃO DA MESMA PEÇA
  // =======================================================

  function handleAnotherGeneration() {
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

          {step === 1 ? (

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
                isGenerating
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
