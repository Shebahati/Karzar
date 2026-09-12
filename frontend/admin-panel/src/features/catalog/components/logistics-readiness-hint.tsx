"use client";

type Tri = "unknown" | "true" | "false";
type ShipClass = "unknown" | "parcel" | "freight_only";

export function LogisticsReadinessHint(props: {
  shippingClass: ShipClass;
  fragile: Tri;
  liquid: Tri;
  weight: string;
  length: string;
  width: string;
  height: string;
}) {
  const weightOk = props.weight.trim() !== "" && Number(props.weight) > 0;
  const dimsOk =
    props.length.trim() !== "" &&
    Number(props.length) > 0 &&
    props.width.trim() !== "" &&
    Number(props.width) > 0 &&
    props.height.trim() !== "" &&
    Number(props.height) > 0;
  const classOk = props.shippingClass === "parcel";
  const freight = props.shippingClass === "freight_only";
  const hazardsOk = props.fragile !== "unknown" && props.liquid !== "unknown";

  let label = "وضعیت لجستیک: نامشخص / ناقص";
  if (freight) {
    label = "وضعیت لجستیک: فقط باربری (خارج از مسیر پستکس بسته‌ای)";
  } else if (classOk && weightOk && dimsOk && hazardsOk) {
    label = "وضعیت لجستیک: آمادهٔ مرسوله بسته‌ای (پس از ذخیره)";
  }

  return <p className="text-xs text-muted-foreground">{label}</p>;
}
