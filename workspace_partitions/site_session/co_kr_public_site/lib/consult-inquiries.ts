import { randomUUID } from "node:crypto";
import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { consultServiceOptions, type ConsultService } from "@/lib/consult-schema";

export type ConsultInquiryInput = {
  name: string;
  phone: string;
  email?: string;
  service: ConsultService;
  message: string;
  acceptPrivacy: true;
};

type ConsultInquiryRecord = ConsultInquiryInput & {
  id: string;
  submittedAt: string;
  source: "website";
};

type ConsultInquiryValidationInput = Partial<{
  name: string;
  phone: string;
  email: string;
  service: ConsultService | string;
  message: string;
  acceptPrivacy: boolean | string;
}>;

function sanitize(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

function sanitizeMessage(value: string) {
  return value.replace(/\r\n/g, "\n").trim().replace(/\n{3,}/g, "\n\n");
}

function normalizeAcceptPrivacy(value: ConsultInquiryValidationInput["acceptPrivacy"]) {
  return value === true || value === "true" || value === "on";
}

export function validateConsultInquiry(input: ConsultInquiryValidationInput) {
  const name = sanitize(input.name ?? "");
  const phone = sanitize(input.phone ?? "");
  const email = sanitize(input.email ?? "");
  const service = sanitize(input.service ?? "") as ConsultService;
  const message = sanitizeMessage(input.message ?? "");
  const acceptPrivacy = normalizeAcceptPrivacy(input.acceptPrivacy);

  if (name.length < 2 || name.length > 40) {
    return { ok: false as const, message: "이름은 2자 이상 40자 이하로 입력해 주세요." };
  }

  if (!/^[0-9+\-\s()]{8,20}$/.test(phone)) {
    return { ok: false as const, message: "연락 가능한 전화번호를 입력해 주세요." };
  }

  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { ok: false as const, message: "이메일 형식이 올바르지 않습니다." };
  }

  if (!consultServiceOptions.includes(service)) {
    return { ok: false as const, message: "상담 유형을 선택해 주세요." };
  }

  if (message.length < 10 || message.length > 1000) {
    return { ok: false as const, message: "문의 내용은 10자 이상 1000자 이하로 입력해 주세요." };
  }

  if (!acceptPrivacy) {
    return { ok: false as const, message: "개인정보처리방침 동의 후 문의를 접수할 수 있습니다." };
  }

  return {
    ok: true as const,
    value: {
      name,
      phone,
      email,
      service,
      message,
      acceptPrivacy: true as const,
    },
  };
}

async function forwardConsultInquiry(record: ConsultInquiryRecord) {
  const webhookUrl = process.env.CONSULT_WEBHOOK_URL;

  if (!webhookUrl) {
    return;
  }

  try {
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record),
      cache: "no-store",
    });

    if (!response.ok) {
      console.error(`Consult webhook request failed with status ${response.status}`);
    }
  } catch (error) {
    console.error("Consult webhook request failed", error);
  }
}

export async function saveConsultInquiry(input: ConsultInquiryInput) {
  const record: ConsultInquiryRecord = {
    ...input,
    id: randomUUID(),
    submittedAt: new Date().toISOString(),
    source: "website",
  };

  const dataDir = path.join(process.cwd(), "data");
  const outputPath = path.join(dataDir, "consult-inquiries.ndjson");

  await mkdir(dataDir, { recursive: true });
  await appendFile(outputPath, `${JSON.stringify(record)}\n`, "utf8");
  await forwardConsultInquiry(record);

  return record;
}
