import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { Button, Empty, Icons, Modal, Panel, Spinner, StatusBadge, useToast } from '../components/ui';
import { useAuth } from '../lib/auth';

export default function RecipientCatalog() {
  const { user } = useAuth();
  const toast = useToast();

  const _planRank = (plan) => {
    const ranks = { free: 0, pro: 1, max: 2 };
    return ranks[plan] ?? 0;
  };
  const [groups, setGroups] = useState(null);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [purchaseOpen, setPurchaseOpen] = useState(null);
  const [purchaseBusy, setPurchaseBusy] = useState(false);

  const loadGroups = () => {
    let url = '/api/recipient-groups';
    if (selectedCategory) url += '?category_id=' + selectedCategory;
    api(url).then(setGroups).catch((e) => toast(e.message, 'error'));
  };

  const loadCategories = () => {
    api('/api/categories').then(setCategories).catch(() => {});
  };

  useEffect(() => { loadCategories(); }, []);
  useEffect(() => { loadGroups(); }, [selectedCategory]);

  const handlePurchase = async (group) => {
    setPurchaseBusy(true);
    try {
      const res = await api('/api/recipient-groups/' + group.id + '/purchase', { method: 'POST' });
      toast(res.message || 'Access granted', 'success');
      setPurchaseOpen(null);
      loadGroups();
    } catch (e) {
      toast(e.message || 'Failed to purchase', 'error');
    } finally {
      setPurchaseBusy(false);
    }
  };

  const viewRecipients = (group) => {
    if (group.has_access) {
      window.location.href = '/recipients?group=' + group.id;
    } else {
      setPurchaseOpen(group);
    }
  };

  return (
    <Layout title="Recipient Catalog" breadcrumb={<span>Recipient Catalog</span>}>
      <div className="toolbar">
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="select"
          style={{ minWidth: 160 }}
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      <Panel>
        {groups === null ? (
          <Spinner />
        ) : groups.length === 0 ? (
          <Empty message="No recipient groups available in the catalog." />
        ) : (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {groups.map((g) => (
              <div key={g.id} className="stat-card" style={{ minHeight: 200 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <h3 style={{ fontSize: 16, margin: 0 }}>{g.name}</h3>
                    <div className="muted" style={{ fontSize: 12 }}>{g.description || 'No description'}</div>
                  </div>
                  <StatusBadge status={g.is_free ? 'Free' : 'Paid'} tone={g.is_free ? 'green' : 'blue'} />
                </div>

                <div style={{ margin: '8px 0' }}>
                  <div className="flex" style={{ alignItems: 'center', gap: 6 }}>
                    {Icons.send}
                    <span><b>{g.recipient_count}</b> contacts</span>
                  </div>
                  {g.category_name && (
                    <div className="muted" style={{ fontSize: 12 }}>{g.category_name}</div>
                  )}
                </div>

                <div style={{ margin: '12px 0', padding: '8px', background: 'var(--panel)', borderRadius: 6 }}>
                  <div className="flex" style={{ justifyContent: 'space-between', fontSize: 13 }}>
                    <span>Price</span>
                    <b>${g.price.toFixed(2)}</b>
                  </div>
                  <div className="flex" style={{ justifyContent: 'space-between', fontSize: 13 }}>
                    <span>Required</span>
                    <b>{g.required_subscription.charAt(0).toUpperCase() + g.required_subscription.slice(1)}</b>
                  </div>
                </div>

                <div style={{ marginTop: 'auto', paddingTop: 12 }}>
                  {g.has_access ? (
                    <Button variant="secondary" style={{ width: '100%' }} onClick={() => viewRecipients(g)}>
                      {Icons.eye} View Recipients
                    </Button>
                  ) : (
                    <Button style={{ width: '100%' }} onClick={() => viewRecipients(g)}>
                      {g.price > 0 ? '$' + g.price.toFixed(2) + ' · Get Access' : 'Get Access'}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Modal
        open={!!purchaseOpen}
        title={purchaseOpen?.name || ''}
        onClose={() => setPurchaseOpen(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPurchaseOpen(null)} disabled={purchaseBusy}>Cancel</Button>
            <Button onClick={() => handlePurchase(purchaseOpen)} disabled={purchaseBusy}>
              {purchaseBusy ? 'Processing…' : (purchaseOpen?.price > 0 ? 'Purchase $' + purchaseOpen.price.toFixed(2) : 'Get Access')}
            </Button>
          </>
        }
      >
        {purchaseOpen && (
          <div>
            <p><b>{purchaseOpen.recipient_count}</b> contacts in this group.</p>
            <p className="muted">
              Price: <b>${purchaseOpen.price.toFixed(2)}</b>
            </p>
            <p className="muted">
              Required subscription: <b>{purchaseOpen.required_subscription}</b>
            </p>
            <p className="muted">Your plan: <b>{user?.plan || 'free'}</b></p>
            {!purchaseOpen.is_free && _planRank(user?.plan || 'free') < _planRank(purchaseOpen.required_subscription) && (
              <p style={{ color: 'var(--danger)', fontSize: 13 }}>
                You need a {purchaseOpen.required_subscription} subscription to access this group.
              </p>
            )}
          </div>
        )}
       </Modal>
    </Layout>
  );
}
