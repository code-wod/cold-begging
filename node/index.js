const fs = require('fs');
const path = require('path');
const ExcelJS = require('exceljs');
const nodemailer = require('nodemailer');
const axios = require('axios');
const cheerio = require('cheerio');
const { AnthropicClient } = require('@anthropic-ai/sdk');

const anthropicKey = process.env.ANTHROPIC_API_KEY;
const gmailUser = process.env.SENDER_EMAIL;
const gmailAppPassword = process.env.GMAIL_APP_PASSWORD;

const excelPath = process.argv[2] || 'emails.xlsx';
const dryRun = process.argv.includes('--dry-run');
const maxEmailsArg = process.argv.find(arg => arg.startsWith('--max='));
const maxEmails = maxEmailsArg ? Number(maxEmailsArg.split('=')[1]) : 25;

async function readExcel(filePath) {
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.readFile(filePath);
  const worksheet = workbook.getWorksheet(1);
  const rows = [];
  worksheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) {
      return;
    }

    const email = row.getCell(1).text.trim();
    if (!email) {
      return;
    }

    rows.push({
      email,
      companyName: row.getCell(2).text.trim(),
      industry: row.getCell(3).text.trim(),
      website: row.getCell(4).text.trim(),
      jobRole: row.getCell(5).text.trim(),
      positionLevel: row.getCell(6).text.trim(),
      linkedinUrl: row.getCell(7).text.trim(),
      employeeCount: row.getCell(8).text.trim(),
      fundingStatus: row.getCell(9).text.trim(),
      recentNews: row.getCell(10).text.trim(),
      contactPersonName: row.getCell(11).text.trim()
    });
  });
  return rows;
}

async function scrapeCompanyWebsite(website) {
  if (!website) {
    return { description: '', aboutText: '', hasCareerPage: false };
  }

  const url = website.startsWith('http') ? website : `https://${website}`;
  try {
    const response = await axios.get(url, { timeout: 7000 });
    const $ = cheerio.load(response.data);
    return {
      description: $('meta[name="description"]').attr('content') || '',
      aboutText: $('section[id*="about"]').text().trim().slice(0, 250) || '',
      hasCareerPage: $('a').filter((_, el) => $(el).text().toLowerCase().includes('career')).length > 0
    };
  } catch (error) {
    console.warn(`Could not scrape ${url}: ${error.message}`);
    return { description: '', aboutText: '', hasCareerPage: false };
  }
}

function buildPrompt(emailData, companyInfo) {
  return `Create a personalized cold email for a job opportunity:\n\nCompany: ${emailData.companyName}\nTarget Role: ${emailData.jobRole}\nPosition Level: ${emailData.positionLevel}\nIndustry: ${emailData.industry}\nCompany Description: ${companyInfo.description || companyInfo.aboutText || 'No public description available.'}\n\nRequirements:\n- Subject line should be unique and NOT generic\n- 3-4 short paragraphs\n- Mention something specific about the company\n- Clear CTA for a call\n- Professional but conversational\n\nFormat:\nSUBJECT: [subject]\nBODY:\n[body text]`;
}

async function generateEmail(emailData, companyInfo) {
  if (!anthropicKey) {
    const subject = `Quick chat about ${emailData.companyName}`;
    const body = `Hi ${emailData.contactPersonName || 'there'},\n\nI noticed ${emailData.companyName} is doing compelling work in ${emailData.industry}. I wanted to reach out about supporting your ${emailData.jobRole} needs at the ${emailData.positionLevel} level.\n\nWould you be open to a brief conversation this week?\n\nBest regards,\n[Your Name]`;
    return { subject, body };
  }

  const client = new AnthropicClient({ apiKey: anthropicKey });
  const prompt = buildPrompt(emailData, companyInfo);

  try {
    const response = await client.responses.create({
      model: 'claude-3.5',
      input: prompt,
      max_tokens_to_sample: 400
    });

    const text = response.output[0].contents[0].text || '';
    const cleaned = text.replace(/```/g, '').trim();
    const [subjectPart, ...bodyParts] = cleaned.split('BODY:');
    return {
      subject: subjectPart.replace('SUBJECT:', '').trim(),
      body: bodyParts.join('BODY:').trim()
    };
  } catch (error) {
    console.warn('AI generation failed:', error.message);
    return {
      subject: `Quick chat about ${emailData.companyName}`,
      body: `Hi ${emailData.contactPersonName || 'there'},\n\nI noticed ${emailData.companyName} is doing compelling work in ${emailData.industry}. I wanted to reach out about supporting your ${emailData.jobRole} needs at the ${emailData.positionLevel} level.\n\nWould you be open to a brief conversation this week?\n\nBest regards,\n[Your Name]`
    };
  }
}

async function sendEmail(to, subject, body) {
  if (!gmailUser || !gmailAppPassword) {
    throw new Error('SENDER_EMAIL and GMAIL_APP_PASSWORD environment variables are required for SMTP sending');
  }

  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: gmailUser,
      pass: gmailAppPassword
    }
  });

  const htmlBody = body.replace(/\n/g, '<br>');
  await transporter.sendMail({
    from: gmailUser,
    to,
    subject,
    html: htmlBody
  });
}

async function run() {
  const emails = await readExcel(path.resolve(excelPath));
  const limit = Math.min(emails.length, maxEmails);
  console.log(`Processing ${limit} rows from ${excelPath}`);

  for (let i = 0; i < limit; i += 1) {
    const row = emails[i];
    console.log(`\n[${i + 1}/${limit}] ${row.companyName} <${row.email}>`);
    const companyInfo = await scrapeCompanyWebsite(row.website);
    const { subject, body } = await generateEmail(row, companyInfo);

    if (dryRun) {
      console.log('DRY RUN:');
      console.log('SUBJECT:', subject);
      console.log('BODY:\n', body);
    } else {
      try {
        await sendEmail(row.email, subject, body);
        console.log('✓ Sent');
      } catch (error) {
        console.error('✗ Failed to send:', error.message);
      }
    }

    await new Promise((resolve) => setTimeout(resolve, 2000));
  }

  console.log('\nCompleted');
}

run().catch((error) => {
  console.error('Fatal error:', error.message);
  process.exit(1);
});
