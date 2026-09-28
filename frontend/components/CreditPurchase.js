import { useState } from 'react';
import { useAuth } from '../lib/auth';
import { api } from '../lib/api';
import { useToast } from './ui';

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: 49,
    credits: 200,
    period: 'one-time',
    desc: 'Send up to 200 cold emails',
    badge: '',
    color: '#6366f1',
    icon: '&#9889;',
  },
  {
    id: 'pro_monthly',
    name: 'Pro',
    price: 99,
    credits: 1199,
    period: 'monthly',
    desc: 'Send up to 1,199 cold emails/mo',
    badge: 'POPULAR',
    color: '#f59e0b',
    icon: '&#9733;',
  },
];

export default function CreditPurchase({ onPurchased }) {
  const toast = useToast();
  const { user } = useAuth();
  const [loading, setLoading] = useState(null);
  const isPro = user?.plan === 'pro';

  const handlePurchase = async (plan) => {
    setLoading(plan.id);
    try {
      const order = await api('/api/billing/create-order', {
        method: 'POST',
        body: { pack_id: plan.id },
      });

      const options = {
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: 'Codessy',
        description: plan.desc,
        order_id: order.order_id,
        handler: async (response) => {
          try {
            const result = await api('/api/billing/verify-payment', {
              method: 'POST',
              body: {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                pack_id: plan.id,
              },
            });
            toast(`Payment successful! ${result.credits_added} credits added.`, 'success');
            if (onPurchased) onPurchased(result);
          } catch (e) {
            toast(`Payment received but activation failed. Contact support.`, 'error');
          }
          setLoading(null);
        },
        modal: {
          ondismiss: () => setLoading(null),
        },
      };

      if (!window.Razorpay) {
        toast('Payment system is loading. Please try again in a moment.', 'error');
        setLoading(null);
        return;
      }

      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', (response) => {
        toast(`Payment failed: ${response.error.description}`, 'error');
        setLoading(null);
      });
      rzp.open();
    } catch (e) {
      toast(e.message, 'error');
      setLoading(null);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, maxWidth: 520 }}>
      {PLANS.map((plan) => {
        const isPopular = plan.badge === 'POPULAR';
        const isHighlighted = isPopular;
        const isCurrentPlan = (plan.id === 'pro_monthly' && isPro) || (plan.id === 'starter' && !isPro);

        return (
          <div
            key={plan.id}
            onClick={() => !isCurrentPlan && handlePurchase(plan)}
            style={{
              position: 'relative',
              border: `2px solid ${isCurrentPlan ? plan.color : isHighlighted ? plan.color + '66' : 'var(--border)'}`,
              borderRadius: 14,
              padding: '28px 20px',
              textAlign: 'center',
              cursor: isCurrentPlan ? 'default' : loading ? 'wait' : 'pointer',
              transition: 'all 0.3s cubic-bezier(0.22, 1, 0.36, 1)',
              background: isCurrentPlan
                ? `linear-gradient(180deg, ${plan.color}08, ${plan.color}04)`
                : isHighlighted ? `${plan.color}05` : 'var(--panel)',
              opacity: loading && loading !== plan.id ? 0.5 : 1,
              boxShadow: isHighlighted ? `0 4px 24px ${plan.color}15` : '0 1px 3px rgba(0,0,0,0.04)',
            }}
            onMouseEnter={(e) => {
              if (!isCurrentPlan) {
                e.currentTarget.style.transform = 'translateY(-6px)';
                e.currentTarget.style.boxShadow = `0 12px 32px ${plan.color}20`;
              }
            }}
            onMouseLeave={(e) => {
              if (!isCurrentPlan) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = isHighlighted ? `0 4px 24px ${plan.color}15` : '0 1px 3px rgba(0,0,0,0.04)';
              }
            }}
          >
            {isCurrentPlan && (
              <div style={{
                position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                background: `linear-gradient(135deg, ${plan.color}, ${plan.color}cc)`,
                color: '#fff', fontSize: 10, fontWeight: 700,
                padding: '4px 14px', borderRadius: 20, letterSpacing: 0.5,
                boxShadow: `0 2px 8px ${plan.color}40`,
              }}>
                CURRENT PLAN
              </div>
            )}
            {!isCurrentPlan && plan.badge && (
              <div style={{
                position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                background: `linear-gradient(135deg, ${plan.color}, ${plan.color}cc)`,
                color: '#fff', fontSize: 10, fontWeight: 700,
                padding: '4px 14px', borderRadius: 20, letterSpacing: 0.5,
                boxShadow: `0 2px 8px ${plan.color}40`,
              }}>
                {plan.badge}
              </div>
            )}

            <div style={{
              fontSize: 15, fontWeight: 700,
              marginBottom: 12, marginTop: (plan.badge || isCurrentPlan) ? 10 : 0,
              color: plan.color, letterSpacing: -0.2,
            }}>
              {plan.name}
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 2, marginBottom: 4 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>₹</span>
              <span style={{ fontSize: 40, fontWeight: 800, lineHeight: 1, letterSpacing: -1, color: 'var(--text)' }}>{plan.price}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
              {plan.period === 'one-time' ? 'one-time payment' : 'per month'}
            </div>

            <div style={{ fontSize: 13, color: 'var(--text)', marginBottom: 16, fontWeight: 500 }}>
              {plan.desc}
            </div>

            <div style={{
              background: isCurrentPlan ? plan.color + '15' : loading === plan.id ? 'var(--muted)' : `linear-gradient(135deg, ${plan.color}, ${plan.color}dd)`,
              color: isCurrentPlan ? plan.color : '#fff',
              padding: '11px 0',
              borderRadius: 10,
              fontSize: 14, fontWeight: 700,
              transition: 'all 0.2s',
              boxShadow: isCurrentPlan ? 'none' : `0 2px 8px ${plan.color}30`,
              letterSpacing: -0.1,
            }}>
              {isCurrentPlan ? 'Current Plan' : loading === plan.id ? 'Processing...' : 'Buy Now'}
            </div>

            {plan.period === 'monthly' && !isCurrentPlan && (
              <div style={{ fontSize: 11, color: plan.color, marginTop: 10, fontWeight: 600, opacity: 0.8 }}>
                Just ₹0.08 per email
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
