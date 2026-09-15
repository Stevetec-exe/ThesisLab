import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { randomUUID } from "node:crypto";

const S3Url = process.env.S3_URL ?? "http://localhost:8333/context";

const url = new URL(S3Url);
const bucket = url.pathname.replace(/^\/|\/$/g, "");

const s3 = new S3Client({
  endpoint: `${url.protocol}//${url.host}`,
  region: process.env.AWS_REGION ?? "us-east-1",
  forcePathStyle: true, // useful for S3-compatible storage such as MinIO
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID ?? "minioadmin",
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY ?? "minioadmin",
  },
});

export async function upload(buffer: Buffer): Promise<string> {
  const id = randomUUID();

  await s3.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: id,
      Body: buffer,
    }),
  );

  return id;
}