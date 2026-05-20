import type { NextApiRequest, NextApiResponse } from 'next'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).end()
  const { buyer_name, buyer_email, buyer_cpf } = req.body
  const pdf_id = process.env.NEXT_PUBLIC_DEFAULT_PDF_ID!

  try {
    const r = await fetch(`${BACKEND}/api/checkout/pix`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pdf_id, buyer_name, buyer_email, buyer_cpf }),
    })
    const data = await r.json()
    return res.status(r.status).json(data)
  } catch (err) {
    return res.status(500).json({ error: 'Erro ao criar preferência PIX.' })
  }
}
