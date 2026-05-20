import type { NextApiRequest, NextApiResponse } from 'next'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2024-04-10' })

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).end()

  const { buyer_name, buyer_email, buyer_cpf } = req.body
  if (!buyer_name || !buyer_email) {
    return res.status(400).json({ error: 'Nome e e-mail obrigatórios.' })
  }

  const pdf_id = process.env.NEXT_PUBLIC_DEFAULT_PDF_ID!
  const base   = process.env.NEXT_PUBLIC_BASE_URL!

  try {
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card', 'boleto'],
      line_items: [{
        price_data: {
          currency: 'brl',
          unit_amount: 9700,   // R$ 97,00 — ajustar conforme produto
          product_data: {
            name: 'Python do Zero ao Pro',
            description: 'Produto digital protegido por PDFShield',
          },
        },
        quantity: 1,
      }],
      mode: 'payment',
      customer_email: buyer_email,
      success_url: `${base}/minha-conta?token={CHECKOUT_SESSION_ID}`,
      cancel_url:  `${base}/?cancelado=1`,
      metadata:    { pdf_id, buyer_name, buyer_cpf: buyer_cpf || '' },
      billing_address_collection: 'required',
      locale: 'pt-BR',
    })
    return res.json({ checkout_url: session.url })
  } catch (err: any) {
    console.error('Stripe error:', err.message)
    return res.status(500).json({ error: 'Erro ao criar checkout.' })
  }
}
