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
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, maxWidth: 500 }}>
      {PLANS.map((plan) => {
        const isPopular = plan.badge === 'POPULAR';
        const isBestValue = plan.badge === 'BEST VALUE';
        const isHighlighted = isPopular || isBestValue;
        const isCurrentPlan = (plan.id === 'pro_monthly' && isPro) || (plan.id === 'starter' && !isPro);

        return (
          <div
            key={plan.id}
            onClick={() => !isCurrentPlan && handlePurchase(plan)}
            style={{
              position: 'relative',
              border: `2px solid ${isCurrentPlan ? plan.color : isHighlighted ? plan.color + '88' : 'var(--border)'}`,
              borderRadius: 12,
              padding: '24px 16px',
              textAlign: 'center',
              cursor: isCurrentPlan ? 'default' : loading ? 'wait' : 'pointer',
              transition: 'all 0.2s',
              background: isCurrentPlan ? `${plan.color}10` : isHighlighted ? `${plan.color}08` : 'var(--panel)',
              opacity: loading && loading !== plan.id ? 0.5 : 1,
            }}
            onMouseEnter={(e) => {
              if (!isCurrentPlan) {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = `0 8px 24px ${plan.color}22`;
              }
            }}
            onMouseLeave={(e) => {
              if (!isCurrentPlan) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
          >
            {isCurrentPlan && (
              <div style={{
                position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                background: plan.color, color: '#fff', fontSize: 10, fontWeight: 700,
                padding: '3px 12px', borderRadius: 20, letterSpacing: 0.5,
              }}>
                CURRENT PLAN
              </div>
            )}
            {!isCurrentPlan && plan.badge && (
              <div style={{
                position: 'absolute',
                top: -12,
                left: '50%',
                transform: 'translateX(-50%)',
                background: plan.color,
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '3px 12px',
                borderRadius: 20,
                letterSpacing: 0.5,
              }}>
                {plan.badge}
              </div>
            )}

            <div style={{
              fontSize: 16,
              fontWeight: 700,
              marginBottom: 8,
              marginTop: (plan.badge || isCurrentPlan) ? 8 : 0,
              color: plan.color,
            }}>
              {plan.name}
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 2 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>₹</span>
              <span style={{ fontSize: 36, fontWeight: 800, lineHeight: 1 }}>{plan.price}</span>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>/</span>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                {plan.period === 'one-time' ? 'once' : plan.period === 'monthly' ? 'mo' : 'yr'}
              </span>
            </div>

            <div style={{
              fontSize: 13,
              color: 'var(--muted)',
              marginTop: 8,
              marginBottom: 16,
            }}>
              {plan.desc}
            </div>

            <div style={{
              background: isCurrentPlan ? plan.color + '22' : loading === plan.id ? 'var(--muted)' : plan.color,
              color: isCurrentPlan ? plan.color : '#fff',
              padding: '10px 0',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              transition: 'background 0.2s',
            }}>
              {isCurrentPlan ? 'Current Plan' : loading === plan.id ? 'Processing...' : 'Buy Now'}
            </div>

            {plan.period === 'monthly' && !isCurrentPlan && (
              <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 8, fontWeight: 600 }}>
                Just ₹0.08 per email
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
