import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') return res.status(405).end()
  const { token } = req.query
  if (!token) return res.status(400).json({ error: 'Token ausente.' })

  try {
    const r = await fetch(`${BACKEND}/api/purchase?token=${token}`)
    const data = await r.json()
    return res.status(r.status).json(data)
  } catch {
    return res.status(500).json({ error: 'Erro ao buscar compra.' })
  }
}
