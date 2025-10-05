import Head from 'next/head';
import Link from 'next/link';
import { useState } from 'react';

export default function ContactPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const subject = encodeURIComponent(`Contact from ${name}`);
    const body = encodeURIComponent(`From: ${name} <${email}>\n\n${message}`);
    window.location.href = `mailto:cosmicsparksteam@gmail.com?subject=${subject}&body=${body}`;
  };

  return (
    <>
      <Head>
        <title>Contact</title>
      </Head>
      <div className="min-h-screen space-bg">
        <div className="stars" />
        <div className="sticky top-0 z-50 backdrop-blur-md bg-white/5 border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex justify-end">
            <Link href="/">
              <button className="bg-white/10 text-white px-4 py-2 rounded-lg border border-white/20 hover:bg-white/20">Home</button>
            </Link>
          </div>
        </div>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-bold text-white mb-6">Contact</h1>

          <div className="glass rounded-2xl p-6 text-white">
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-300 mb-1">Name</label>
                <input value={name} onChange={e => setName(e.target.value)} className="w-full bg-white/10 text-white border border-white/20 rounded px-3 py-2 outline-none" required />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Email</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full bg-white/10 text-white border border-white/20 rounded px-3 py-2 outline-none" required />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Message</label>
                <textarea rows={5} value={message} onChange={e => setMessage(e.target.value)} className="w-full bg-white/10 text-white border border-white/20 rounded px-3 py-2 outline-none" required />
              </div>
              <button className="bg-gradient-to-r from-cyan-500 to-indigo-500 hover:from-cyan-400 hover:to-indigo-400 text-white px-4 py-2 rounded-lg shadow">
                Send Message
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
