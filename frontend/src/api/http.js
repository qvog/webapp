/** Thin fetch wrapper for backend API (proxied via Vite). */

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }

  if (!res.ok) {
    const msg = (data && (data.error || data.detail)) || `HTTP ${res.status}`
    throw new ApiError(msg, res.status)
  }

  return data
}
