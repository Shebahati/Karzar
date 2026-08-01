import { KnowledgeEdgesBrowser } from "@/features/knowledge/components/knowledge-edges-browser";

export default function KnowledgePage() {
  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">دانش محصول</h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          نمای فقط‌خواندنی گراف موج‌۱ (KB-001): سه نوع یال پروجکت‌شده. ویرایش Facts، dual-write و
          طبقه‌بندی دانش هنوز فعال نیست.
        </p>
      </div>
      <KnowledgeEdgesBrowser />
    </div>
  );
}
