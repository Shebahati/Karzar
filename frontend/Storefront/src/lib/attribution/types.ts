export interface AcquisitionCampaign {
  utm_source?: string | null;
  utm_medium?: string | null;
  utm_campaign?: string | null;
}

export interface AcquisitionTouch {
  source: string;
  source_subtype?: string | null;
  method: string;
  landing_path?: string | null;
  campaign?: AcquisitionCampaign | null;
  captured_at: string;
}

export interface AttributionState {
  first_touch: AcquisitionTouch | null;
  last_non_direct_touch: AcquisitionTouch | null;
}
