export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const text = await response.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError(response.status, "Phản hồi API không hợp lệ.");
  }
  if (!response.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data ? data.detail : null;
    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : JSON.stringify(detail || "Không thể hoàn tất yêu cầu."),
    );
  }
  return data as T;
}
export function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}
export function errorText(error: unknown): string {
  if (error instanceof ApiError && error.status === 409)
    return (
      "Hồ sơ hoặc đề xuất đã thay đổi. Nội dung nhập được giữ lại; tải lại dữ liệu và rà soát trước khi gửi lại. " +
      error.message
    );
  return error instanceof Error
    ? error.message
    : "Không thể kết nối. Vui lòng thử lại.";
}
