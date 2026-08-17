// ==========================================================
// MARIED STUDIO
// PREPARAÇÃO AUTOMÁTICA DE IMAGENS
// ==========================================================

export type ImagePreparationResult = {
  file: File;

  originalWidth: number;
  originalHeight: number;

  finalWidth: number;
  finalHeight: number;

  wasResized: boolean;
  wasUpscaled: boolean;
  wasCompressed: boolean;

  originalSize: number;
  finalSize: number;
};


export class ImagePreparationError extends Error {
  code: string;

  constructor(
    message: string,
    code: string
  ) {
    super(message);

    this.name =
      "ImagePreparationError";

    this.code =
      code;
  }
}


// ==========================================================
// CONFIGURAÇÕES
// ==========================================================

// Mínimo exigido pelo backend
const MIN_WIDTH = 500;
const MIN_HEIGHT = 500;


// Abaixo disso não vale ampliar.
// A imagem provavelmente já perdeu
// informação demais.
const HARD_MIN_WIDTH = 320;
const HARD_MIN_HEIGHT = 320;


// Evita enviar fotos gigantes de celular.
// 2400px já é mais do que suficiente
// para o fluxo atual.
const MAX_LONG_SIDE = 2400;


// Qualidade JPEG
const JPEG_QUALITY = 0.9;


// Limite final desejado.
// Ainda mantemos abaixo dos 15 MB
// permitidos pelo backend.
const TARGET_MAX_FILE_SIZE =
  6 * 1024 * 1024;


// ==========================================================
// CARREGAR IMAGEM
// ==========================================================

async function loadImage(
  file: File
): Promise<HTMLImageElement> {
  return new Promise(
    (
      resolve,
      reject
    ) => {
      const image =
        new Image();

      const objectUrl =
        URL.createObjectURL(
          file
        );

      image.onload = () => {
        URL.revokeObjectURL(
          objectUrl
        );

        resolve(
          image
        );
      };

      image.onerror = () => {
        URL.revokeObjectURL(
          objectUrl
        );

        reject(
          new ImagePreparationError(
            "Não conseguimos abrir essa foto. Tente escolher outra imagem.",
            "IMAGE_DECODE_FAILED"
          )
        );
      };

      image.src =
        objectUrl;
    }
  );
}


// ==========================================================
// CALCULAR DIMENSÕES
// ==========================================================

function calculateFinalSize(
  width: number,
  height: number
) {
  let finalWidth =
    width;

  let finalHeight =
    height;

  let wasUpscaled =
    false;

  let wasResized =
    false;


  // ========================================================
  // IMAGEM PEQUENA
  // Amplia somente quando ainda existe
  // uma quantidade razoável de informação.
  // ========================================================

  if (
    width < MIN_WIDTH ||
    height < MIN_HEIGHT
  ) {
    const scale =
      Math.max(
        MIN_WIDTH / width,
        MIN_HEIGHT / height
      );

    finalWidth =
      Math.round(
        width * scale
      );

    finalHeight =
      Math.round(
        height * scale
      );

    wasUpscaled =
      true;

    wasResized =
      true;
  }


  // ========================================================
  // IMAGEM GRANDE
  // Reduz automaticamente mantendo proporção.
  // ========================================================

  const longSide =
    Math.max(
      finalWidth,
      finalHeight
    );

  if (
    longSide >
    MAX_LONG_SIDE
  ) {
    const scale =
      MAX_LONG_SIDE /
      longSide;

    finalWidth =
      Math.round(
        finalWidth *
        scale
      );

    finalHeight =
      Math.round(
        finalHeight *
        scale
      );

    wasResized =
      true;
  }


  return {
    finalWidth,
    finalHeight,
    wasUpscaled,
    wasResized,
  };
}


// ==========================================================
// CANVAS → BLOB
// ==========================================================

function canvasToBlob(
  canvas: HTMLCanvasElement,
  quality: number
): Promise<Blob> {
  return new Promise(
    (
      resolve,
      reject
    ) => {
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(
              new ImagePreparationError(
                "Não conseguimos preparar essa foto. Tente novamente.",
                "CANVAS_EXPORT_FAILED"
              )
            );

            return;
          }

          resolve(
            blob
          );
        },

        "image/jpeg",

        quality
      );
    }
  );
}


// ==========================================================
// NOME DO ARQUIVO
// ==========================================================

function buildOutputName(
  originalName: string
) {
  const withoutExtension =
    originalName.replace(
      /\.[^/.]+$/,
      ""
    );

  return `${withoutExtension}-maried.jpg`;
}


// ==========================================================
// PREPARAÇÃO PRINCIPAL
// ==========================================================

export async function prepareImage(
  originalFile: File
): Promise<ImagePreparationResult> {

  // ========================================================
  // TIPO
  // ========================================================

  const allowedTypes = [
    "image/jpeg",
    "image/png",
    "image/webp",
  ];

  if (
    !allowedTypes.includes(
      originalFile.type
    )
  ) {
    throw new ImagePreparationError(
      "Esse formato de foto ainda não é compatível. Escolha uma foto JPG, PNG ou WEBP.",
      "INVALID_FORMAT"
    );
  }


  // ========================================================
  // TAMANHO BRUTO
  // ========================================================

  if (
    originalFile.size >
    30 * 1024 * 1024
  ) {
    throw new ImagePreparationError(
      "Essa foto está muito pesada. Tente tirar outra foto ou escolher uma imagem diferente.",
      "FILE_TOO_LARGE"
    );
  }


  // ========================================================
  // DECODIFICAR
  // ========================================================

  const image =
    await loadImage(
      originalFile
    );


  const originalWidth =
    image.naturalWidth;

  const originalHeight =
    image.naturalHeight;


  // ========================================================
  // MUITO PEQUENA
  // ========================================================

  if (
    originalWidth <
      HARD_MIN_WIDTH ||
    originalHeight <
      HARD_MIN_HEIGHT
  ) {
    throw new ImagePreparationError(
      "Essa foto está com pouca qualidade para gerar um bom resultado. Tire outra foto mais próxima da peça.",
      "IMAGE_TOO_SMALL"
    );
  }


  // ========================================================
  // DIMENSÕES FINAIS
  // ========================================================

  const {
    finalWidth,
    finalHeight,
    wasUpscaled,
    wasResized,
  } =
    calculateFinalSize(
      originalWidth,
      originalHeight
    );


  // ========================================================
  // CANVAS
  // ========================================================

  const canvas =
    document.createElement(
      "canvas"
    );

  canvas.width =
    finalWidth;

  canvas.height =
    finalHeight;


  const context =
    canvas.getContext(
      "2d"
    );


  if (!context) {
    throw new ImagePreparationError(
      "Não conseguimos preparar essa foto neste dispositivo.",
      "CANVAS_NOT_SUPPORTED"
    );
  }


  // ========================================================
  // FUNDO BRANCO
  //
  // Importante para PNGs transparentes.
  // ========================================================

  context.fillStyle =
    "#FFFFFF";

  context.fillRect(
    0,
    0,
    finalWidth,
    finalHeight
  );


  // ========================================================
  // DESENHAR
  // ========================================================

  context.imageSmoothingEnabled =
    true;

  context.imageSmoothingQuality =
    "high";


  context.drawImage(
    image,
    0,
    0,
    finalWidth,
    finalHeight
  );


  // ========================================================
  // EXPORTAR
  // ========================================================

  let quality =
    JPEG_QUALITY;

  let blob =
    await canvasToBlob(
      canvas,
      quality
    );


  // ========================================================
  // COMPRESSÃO ADAPTATIVA
  // ========================================================

  while (
    blob.size >
      TARGET_MAX_FILE_SIZE &&
    quality >
      0.72
  ) {
    quality -=
      0.05;

    blob =
      await canvasToBlob(
        canvas,
        quality
      );
  }


  // ========================================================
  // NOVO FILE
  // ========================================================

  const preparedFile =
    new File(
      [
        blob,
      ],

      buildOutputName(
        originalFile.name
      ),

      {
        type:
          "image/jpeg",

        lastModified:
          Date.now(),
      }
    );


  return {
    file:
      preparedFile,

    originalWidth,
    originalHeight,

    finalWidth,
    finalHeight,

    wasResized,

    wasUpscaled,

    wasCompressed:
      preparedFile.size <
      originalFile.size,

    originalSize:
      originalFile.size,

    finalSize:
      preparedFile.size,
  };
}