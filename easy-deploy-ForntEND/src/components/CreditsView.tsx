import React from 'react';
import { User, ShieldAlert, Copyright, Info, Award, X } from 'lucide-react';
import { ActiveTab } from '../types';

interface CreditsViewProps {
  onSetTab: (tab: ActiveTab) => void;
}

export default function CreditsView({ onSetTab }: CreditsViewProps) {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title Header area matching current layout with responsive details */}
      <div 
        className="backdrop-blur-md p-6 rounded-2xl border flex flex-col sm:flex-row items-center gap-5 justify-between"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)'
        }}
      >
        <div className="flex items-center gap-4">
          <div 
            className="w-14 h-14 rounded-xl border flex items-center justify-center select-none shadow"
            style={{
              backgroundColor: 'var(--theme-bg-well)',
              borderColor: 'var(--theme-border-well)'
            }}
          >
            {/* Elegant Coat of Arms representation or logo icon */}
            <Award className="w-8 h-8 animate-pulse" style={{ color: 'var(--theme-accent-primary)' }} />
          </div>
          <div>
            <h1 className="text-lg font-bold font-sans tracking-tight mb-1 flex items-center gap-2" style={{ color: 'var(--theme-text-primary)' }}>
              Acerca de Easy Deploy <span className="text-xs font-mono" style={{ color: 'var(--theme-accent-primary)' }}>v2.2.5.28</span>
            </h1>
            <p className="text-xs font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
              Créditos del proyecto y reparto interno de desarrollo declarado para el programa.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-bold shrink-0 self-end sm:self-center" style={{ color: 'var(--theme-text-secondary)', opacity: 0.8 }}>
          v2.2.5.28
        </span>
      </div>

      {/* Authors Area container */}
      <div 
        className="border rounded-2xl p-6 space-y-6"
        style={{
          backgroundColor: 'var(--theme-bg-card)',
          borderColor: 'var(--theme-border-card)',
          color: 'var(--theme-text-primary)'
        }}
      >
        
        {/* Author 1 Card */}
        <div 
          className="border rounded-xl p-5 transition-colors"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <h3 className="text-sm font-bold font-sans mb-3 border-b pb-2 flex items-center gap-2" style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-card)' }}>
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" style={{ backgroundColor: 'var(--theme-accent-primary)' }} />
            Juan Jesús Cañas Ramirez
          </h3>
          <ul className="space-y-2 text-[11px] font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            <li className="flex items-start gap-2">
              <span className="font-bold select-none" style={{ color: 'var(--theme-accent-primary)' }}>-</span>
              <span>Idea principal fundamental de desarrollo del programa y parte de redes.</span>
            </li>
            <li className="flex items-start gap-11 sm:gap-2">
              <span className="font-bold select-none" style={{ color: 'var(--theme-accent-primary)' }}>-</span>
              <span><strong>Redes:</strong> Switch Allied, Switch Cisco, Router, ASA, Checkpoint, Topo e IP.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold select-none" style={{ color: 'var(--theme-accent-primary)' }}>-</span>
              <span>Script Crear usuarios EXC.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold select-none" style={{ color: 'var(--theme-accent-primary)' }}>-</span>
              <span>Guía Exchange.</span>
            </li>
          </ul>
        </div>

        {/* Author 2 Card */}
        <div 
          className="border rounded-xl p-5 transition-colors"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <h3 className="text-sm font-bold font-sans mb-3 border-b pb-2 flex items-center gap-2" style={{ color: 'var(--theme-text-primary)', borderColor: 'var(--theme-border-card)' }}>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            Adrián Mata Cifre
          </h3>
          <ul className="space-y-2 text-[11px] font-sans" style={{ color: 'var(--theme-text-secondary)' }}>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span>Sistemas, menús, Front End, Backend de UI y estética general.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span><strong>Inicio:</strong> Admin, Recursos, Logs, Teclado ESP, Firewall, entorno, roles, CPU, Ping y discos.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span><strong>Sistemas:</strong> DC1/DC2, unión a dominio, Repadmin, D2/D4, .NET 3.5 con ISO local, hora, KMS, SQL, JCHAT, Exchange, SharePoint y Skype.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span><strong>AD/Exchange:</strong> Crear usuarios AD/EXC, avisos, validaciones visuales y estados fijos.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span><strong>Skype:</strong> prerrequisitos offline, permisos de usuario, punteros DNS e instalación desde ISO.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span><strong>Programas/recursos:</strong> Firefox, WinRAR, Adobe Reader, Office + Skype offline, validación de recursos y desmontaje de ISOs.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span><strong>Guías, Seguridad y Consola:</strong> biblioteca PDF, Firewall, Auditoría, Guía rápida, logs y herramientas administrativas.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 font-bold select-none">-</span>
              <span>Apariencia, Versiones, Créditos, ventanas minimizadas y Monitor de ping con favoritos, scroll y formulario integrado.</span>
            </li>
          </ul>
        </div>

        {/* Legal notice area */}
        <div 
          className="border rounded-xl p-4.5 space-y-3"
          style={{
            backgroundColor: 'var(--theme-bg-well)',
            borderColor: 'var(--theme-border-well)'
          }}
        >
          <p className="text-[10px] leading-relaxed font-sans italic" style={{ color: 'var(--theme-text-secondary)' }}>
            <strong>Nota:</strong> esta pantalla es una declaración de créditos del proyecto; no sustituye acuerdos, licencias o contratos externos entre autores.
          </p>
          <div className="flex items-start gap-2.5 text-[10px] leading-relaxed font-sans border-t pt-3" style={{ color: 'var(--theme-text-secondary)', borderColor: 'var(--theme-border-card)', opacity: 0.8 }}>
            <Copyright size={12} className="mt-0.5 shrink-0" />
            <span>
              Copyright © 2026 Easy Deploy. Todos los derechos reservados. Queda prohibida la reproducción total o parcial, distribución, modificación, cesión, venta o cualquier uso lucrativo del programa sin autorización expresa. Los derechos de uso, explotación y distribución quedan reservados.
            </span>
          </div>
        </div>

        {/* Cerrar olive button bottom right */}
        <div className="flex justify-end pt-2">
          <button
            onClick={() => onSetTab('dashboard')}
            className="px-6 py-2 border font-bold rounded-lg text-xs tracking-wider transition-all duration-150 cursor-pointer flex items-center gap-1.5"
            style={{
              backgroundColor: 'var(--theme-bg-well)',
              borderColor: 'var(--theme-border-card)',
              color: 'var(--theme-accent-primary)'
            }}
          >
            <X size={12} style={{ color: 'var(--theme-accent-primary)' }} />
            <span>Cerrar</span>
          </button>
        </div>

      </div>
    </div>
  );
}
