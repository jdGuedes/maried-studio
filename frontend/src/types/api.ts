export type ProductCategory =
  | "EARRING"
  | "NECKLACE"
  | "RING"
  | "BRACELET"
  | "ANKLET";

export type GenerationMode =
  | "STILL"
  | "BODY_DETAIL"
  | "MODEL"
  | "INSTAGRAM";

export type ProductAsset = {
  id: string;
  asset_type: string;
  file: string;
  file_url: string;
  mime_type: string | null;
  width: number | null;
  height: number | null;
  file_size: number | null;
  created_at: string;
};

export type Product = {
  id: string;
  name: string;
  category: ProductCategory;
  status: string;
  original_image_url: string | null;
  assets: ProductAsset[];
  created_at: string;
  updated_at: string;
};

export type SceneTemplate = {
  id: string;
  name: string;
  slug: string;
  generation_mode: GenerationMode;
  category: ProductCategory;
  preview_image: string | null;
  version: number;
  sort_order: number;
};

export type ModelReference = {
  id: string;
  code: string;
  name: string;
  slug: string;
  description: string;
  preview_image: string | null;
  preview_image_url: string | null;
  skin_tone: string;
  hair_color: string;
  age_range: string;
  sort_order: number;
};

export type Generation = {
  id: string;
  product: string;
  mode: GenerationMode;
  scene_template: string | null;
  model_reference: string | null;

  status:
    | "CREATED"
    | "CREDIT_RESERVED"
    | "PROCESSING"
    | "COMPLETED"
    | "FAILED"
    | "CANCELLED";

  failure_type: string;
  provider: string;
  model: string;

  credit_cost: number;
  wallet_balance: number;
  reserved_credits: number;
  available_credits: number;

  retry_count: number;

  image_url: string | null;
  generated_image_id?: string | null;

  error_code: string;
  error_message: string;

  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};
