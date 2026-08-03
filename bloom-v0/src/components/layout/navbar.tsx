import React from 'react';
import Link from 'next/link';

export function Navbar() {
  return (
    <nav className="bg-white p-4 border-b border-gray-200 sticky top-0 z-10">
      <div className="container mx-auto flex justify-between items-center">
        <Link href="/" className="font-bold text-xl text-blue-800 hover:text-blue-600">
          Bloom
        </Link>
        <div className="space-x-4">
          <Link href="/gallery" className="text-gray-700 hover:text-black">
            Gallery
          </Link>
          <Link href="/participate" className="text-gray-700 hover:text-blue-600">
            Participate
          </Link>
          {/* Removed About link */}
          {/* <Link href="/about" className="text-gray-700 hover:text-blue-600">
            About
          </Link> */}
        </div>
      </div>
    </nav>
  );
} 