import type { Metadata } from "next";
import { ArticleView } from "@/components/blog/article-view";
import { catalogService } from "@/services/catalog";
import { extractArticleSeo } from "@/types/content";

type Props = { params: Promise<{ slug: string }> };

const SITE = "https://www.karzartools.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  try {
    const article = await catalogService.getArticle(slug);
    const { seoTitle, seoDescription } = extractArticleSeo(article);
    const description = seoDescription.slice(0, 160) || article.title;
    const canonical = `/blog/${slug}`;
    return {
      title: { absolute: seoTitle },
      description,
      openGraph: {
        type: "article",
        title: seoTitle,
        description,
        url: `${SITE}${canonical}`,
        images: article.cover_image
          ? [{ url: article.cover_image, alt: article.title }]
          : undefined,
        publishedTime: article.published_at,
        authors: [article.author],
        tags: article.tags,
        locale: "fa_IR",
        siteName: "کارزار",
      },
      twitter: {
        card: "summary_large_image",
        title: seoTitle,
        description,
        images: article.cover_image ? [article.cover_image] : undefined,
      },
      alternates: { canonical },
      keywords: article.tags,
    };
  } catch {
    return { title: "مقاله" };
  }
}

export default async function ArticlePage({ params }: Props) {
  const { slug } = await params;
  let jsonLd: Record<string, unknown> | null = null;

  try {
    const article = await catalogService.getArticle(slug);
    const { seoTitle, seoDescription, faqItems } = extractArticleSeo(article);
    const url = `${SITE}/blog/${slug}`;

    const graph: Record<string, unknown>[] = [
      {
        "@type": "Article",
        "@id": `${url}#article`,
        headline: article.title,
        name: seoTitle,
        description: seoDescription,
        image: article.cover_image ? [article.cover_image] : undefined,
        datePublished: article.published_at,
        author: { "@type": "Organization", name: article.author },
        publisher: {
          "@type": "Organization",
          name: "کارزار",
          url: SITE,
        },
        mainEntityOfPage: url,
        inLanguage: "fa-IR",
        keywords: article.tags?.join(", "),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "خانه", item: SITE },
          { "@type": "ListItem", position: 2, name: "مجله کارزار", item: `${SITE}/blog` },
          { "@type": "ListItem", position: 3, name: article.title, item: url },
        ],
      },
    ];

    if (faqItems.length) {
      graph.push({
        "@type": "FAQPage",
        "@id": `${url}#faq`,
        mainEntity: faqItems.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: { "@type": "Answer", text: item.answer },
        })),
      });
    }

    jsonLd = { "@context": "https://schema.org", "@graph": graph };
  } catch {
    jsonLd = null;
  }

  return (
    <>
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      <ArticleView slug={slug} />
    </>
  );
}
